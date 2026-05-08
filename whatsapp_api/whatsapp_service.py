import asyncio
import logging
import re
from time import perf_counter
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import BrowserContext, Page, Playwright, TimeoutError, async_playwright

logger = logging.getLogger(__name__)


class WhatsAppNotLoggedIn(Exception):
    pass


class WhatsAppSendError(Exception):
    pass


class WhatsAppService:
    def __init__(self, session_dir: str, headless: bool = False) -> None:
        self.session_dir = Path(session_dir).expanduser().resolve()
        self.headless = headless
        self.playwright: Playwright | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        logger.info("Starting WhatsApp browser session in %s", self.session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_dir),
            headless=self.headless,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )

        self.page = await self._get_or_create_whatsapp_page()
        await self._open_whatsapp_home()
        logger.info("WhatsApp Web opened. Scan the QR code if this is the first run.")

    async def stop(self) -> None:
        logger.info("Stopping WhatsApp browser session")

        if self.context:
            await self.context.close()
            self.context = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        self.page = None

    async def is_logged_in(self) -> bool:
        page = await self._get_page()

        try:
            if not page.url.startswith("https://web.whatsapp.com"):
                await self._open_whatsapp_home()

            if await page.locator("#pane-side, [data-testid='chat-list'], [aria-label='Chat list']").count() > 0:
                return True

            if await page.locator("canvas, [data-testid='qrcode']").count() > 0:
                return False

            await page.wait_for_selector(
                "#pane-side, [data-testid='chat-list'], [aria-label='Chat list']",
                timeout=3000,
            )
            return True
        except TimeoutError:
            return False
        except Exception:
            logger.exception("Could not check WhatsApp login status")
            return False

    async def send_message(self, number: str, message: str) -> None:
        async with self.lock:
            send_started_at = perf_counter()
            last_step_at = send_started_at

            def log_step(step: str) -> None:
                nonlocal last_step_at
                now = perf_counter()
                logger.info(
                    "WhatsApp send timing for %s: %s took %.2fs, total %.2fs",
                    clean_number,
                    step,
                    now - last_step_at,
                    now - send_started_at,
                )
                last_step_at = now

            if not await self.is_logged_in():
                raise WhatsAppNotLoggedIn("WhatsApp is not logged in")

            clean_number = self._normalize_number(number)
            clean_message = message.strip()

            if not clean_message:
                raise WhatsAppSendError("Message cannot be empty")

            log_step("login check and validation")

            page = await self._get_page()
            chat_url = (
                "https://web.whatsapp.com/send"
                f"?phone={quote(clean_number)}"
                "&app_absent=0"
            )

            logger.info("Opening WhatsApp chat for %s", clean_number)
            await self._open_chat_url(page, chat_url)
            log_step("open chat url")

            composer = await self._wait_for_chat_composer(page)
            log_step("wait for chat composer")

            await composer.fill(clean_message)
            log_step("fill composer")

            await self._send_current_composer_message(page, composer, clean_message)
            log_step("click send")

            await page.wait_for_timeout(250)
            log_step("post-send settle")
            logger.info("Message sent to %s", clean_number)

    async def _get_page(self) -> Page:
        if not self.context:
            raise WhatsAppSendError("WhatsApp browser is not started")

        if self.page and not self.page.is_closed():
            return self.page

        self.page = await self._get_or_create_whatsapp_page()
        return self.page

    async def _get_or_create_whatsapp_page(self) -> Page:
        if not self.context:
            raise WhatsAppSendError("WhatsApp browser is not started")

        pages = [page for page in self.context.pages if not page.is_closed()]
        whatsapp_pages = [page for page in pages if page.url.startswith("https://web.whatsapp.com")]

        page = whatsapp_pages[0] if whatsapp_pages else await self.context.new_page()

        for old_page in pages:
            if old_page != page and old_page.url in {"about:blank", "chrome://new-tab-page/"}:
                await old_page.close()

        return page

    async def _open_whatsapp_home(self) -> None:
        page = await self._get_page()
        await page.goto("https://web.whatsapp.com", wait_until="load", timeout=90_000)
        await page.wait_for_timeout(5000)

        if page.url == "about:blank":
            raise WhatsAppSendError("WhatsApp Web opened a blank page. Restart Chromium and try again.")

    async def _open_chat_url(self, page: Page, chat_url: str) -> None:
        started_at = perf_counter()

        if not page.url.startswith("https://web.whatsapp.com"):
            await self._open_whatsapp_home()
            logger.info("WhatsApp chat timing: open home took %.2fs", perf_counter() - started_at)

        try:
            await page.goto(chat_url, wait_until="domcontentloaded", timeout=15_000)
            logger.info(
                "WhatsApp chat timing: navigate to chat URL took %.2fs. Current URL: %s",
                perf_counter() - started_at,
                page.url,
            )
        except TimeoutError:
            logger.warning(
                "WhatsApp chat URL navigation timed out after %.2fs. Current URL: %s",
                perf_counter() - started_at,
                page.url,
            )

        if page.url == "about:blank":
            raise WhatsAppSendError("WhatsApp opened a blank page while opening the chat")

        body_text = await page.locator("body").inner_text(timeout=5000)
        logger.info("WhatsApp chat timing: read body text took %.2fs", perf_counter() - started_at)
        if not body_text.strip():
            await page.reload(wait_until="load", timeout=90_000)
            await page.wait_for_timeout(5000)
            logger.info("WhatsApp chat timing: blank body reload took %.2fs", perf_counter() - started_at)

    async def _send_current_composer_message(self, page: Page, composer, message: str) -> None:
        started_at = perf_counter()

        await composer.press("Enter", timeout=1500)
        logger.info("WhatsApp composer Enter pressed after %.2fs", perf_counter() - started_at)
        if await self._composer_cleared(page, composer, message):
            return

        logger.warning(
            "WhatsApp composer still contains message after Enter; trying send button. Elapsed %.2fs",
            perf_counter() - started_at,
        )

        send_icon = page.locator("span[data-icon='send']").last
        try:
            if await send_icon.count() > 0 and await send_icon.is_visible(timeout=1000):
                await send_icon.evaluate(
                    """
                    icon => {
                        const control = icon.closest("button,[role='button']");
                        if (control) control.click();
                    }
                    """
                )
                logger.info("WhatsApp send control clicked after %.2fs", perf_counter() - started_at)
                if await self._composer_cleared(page, composer, message):
                    return
        except TimeoutError:
            pass

        raise WhatsAppSendError("Message was typed, but WhatsApp did not send it")

    async def _composer_cleared(self, page: Page, composer, message: str) -> bool:
        for _ in range(20):
            current_text = (await composer.inner_text(timeout=500)).strip()
            if message not in current_text:
                return True
            await page.wait_for_timeout(100)

        return False

    def _normalize_number(self, number: str) -> str:
        clean_number = re.sub(r"\D", "", number)
        if not clean_number:
            raise WhatsAppSendError("Phone number is invalid")
        return clean_number

    async def _wait_for_chat_composer(self, page: Page):
        composer_selector = (
            "footer div[contenteditable='true'][role='textbox'], "
            "div[aria-label='Type a message'][contenteditable='true'], "
            "div[aria-placeholder='Type a message'][contenteditable='true'], "
            "div[contenteditable='true'][data-tab='10']"
        )

        for attempt in range(60):
            composer = page.locator(composer_selector).last
            try:
                if await composer.count() > 0 and await composer.is_visible(timeout=250):
                    return composer
            except TimeoutError:
                pass

            if attempt % 4 == 0:
                error_text = await self._page_error_text(page)
                if error_text:
                    raise WhatsAppSendError(error_text)

            await page.wait_for_timeout(250)

        title = await page.title()
        raise WhatsAppSendError(f"Could not open chat or find message box. Current URL: {page.url}. Title: {title}")

    async def _page_error_text(self, page: Page) -> str | None:
        possible_errors = [
            "Phone number shared via url is invalid",
            "Phone number shared through url is invalid",
            "invalid",
        ]

        try:
            body_text = await page.locator("body").inner_text(timeout=500)
        except TimeoutError:
            return None

        lower_body = body_text.lower()

        for error in possible_errors:
            if error.lower() in lower_body:
                return "Phone number is invalid or chat could not be opened"

        return None
