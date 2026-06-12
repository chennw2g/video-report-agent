from __future__ import annotations

import asyncio
import sys
from pathlib import Path


def _usage() -> str:
    return (
        "Usage: python mediacrawler_xhs_detail.py "
        "<output_dir> <note_url> <max_comments>"
    )


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(_usage())

    output_dir = Path(sys.argv[1]).resolve()
    note_url = sys.argv[2]
    max_comments = int(sys.argv[3])
    get_comment = "yes" if max_comments > 0 else "no"

    # This script is executed with cwd set to the MediaCrawler checkout.
    sys.path.insert(0, str(Path.cwd()))

    import config  # type: ignore[import-not-found]
    import main as mediacrawler_main  # type: ignore[import-not-found]

    config.ENABLE_CDP_MODE = True
    config.CDP_CONNECT_EXISTING = False
    config.SAVE_LOGIN_STATE = True
    config.CDP_HEADLESS = False
    config.HEADLESS = False
    config.AUTO_CLOSE_BROWSER = True
    config.ENABLE_GET_WORDCLOUD = False

    sys.argv = [
        "main.py",
        "--platform",
        "xhs",
        "--lt",
        "qrcode",
        "--type",
        "detail",
        "--specified_id",
        note_url,
        "--get_comment",
        get_comment,
        "--get_sub_comment",
        "no",
        "--max_comments_count_singlenotes",
        str(max_comments),
        "--crawler_max_notes_count",
        "1",
        "--max_concurrency_num",
        "1",
        "--save_data_option",
        "jsonl",
        "--save_data_path",
        str(output_dir),
        "--headless",
        "false",
    ]

    try:
        asyncio.run(mediacrawler_main.main())
    finally:
        asyncio.run(mediacrawler_main.async_cleanup())


if __name__ == "__main__":
    main()
