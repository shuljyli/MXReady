import asyncio
import xml.etree.ElementTree as ET
from itertools import pairwise

import pytest
from rich.cells import cell_len

from mxready.tui.app import MXReadyApp

SVG = "{http://www.w3.org/2000/svg}"


async def _rendered_screenshot(app: MXReadyApp) -> str:
    rendered: asyncio.Future[str] = asyncio.get_running_loop().create_future()

    def capture() -> None:
        if not rendered.done():
            rendered.set_result(app.export_screenshot())

    assert app.call_after_refresh(capture)
    return await asyncio.wait_for(rendered, timeout=5)


def test_screenshot_positions_chinese_on_two_terminal_cells(tmp_path):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            root = ET.fromstring(await _rendered_screenshot(app))
            label = next(
                node for node in root.iter(f"{SVG}text") if "迁移检查" in "".join(node.itertext())
            )
            glyphs = list(label)
            assert len(glyphs) > 1
            assert all(node.tag == f"{SVG}tspan" for node in glyphs)
            chinese = next(node for node in glyphs if node.text == "迁")
            ascii_space = next(node for node in glyphs if node.text == "\u00a0")
            cell_width = float(ascii_space.attrib["textLength"])
            assert float(chinese.attrib["textLength"]) == pytest.approx(2 * cell_width)
            for left, right in pairwise(glyphs):
                assert float(right.attrib["x"]) == pytest.approx(
                    float(left.attrib["x"]) + cell_len(left.text or "") * cell_width
                )

    asyncio.run(scenario())


def test_screenshot_mixed_text_preserves_content_and_cell_positions(tmp_path):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test(size=(80, 24)) as pilot:
            value = "MXReady 中文 e\u0301 & <tag>"
            app._write(value)
            await pilot.pause()
            root = ET.fromstring(await _rendered_screenshot(app))
            label = next(
                node
                for node in root.iter(f"{SVG}text")
                if "MXReady" in "".join(node.itertext()) and "中文" in "".join(node.itertext())
            )
            assert "".join(label.itertext()).replace("\u00a0", " ") == value
            assert any(node.text == "e\u0301" for node in label)

    asyncio.run(scenario())
