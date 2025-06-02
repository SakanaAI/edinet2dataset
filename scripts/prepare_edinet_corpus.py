from argparse import ArgumentParser
import os
import json
from edinet2dataset.downloader import Downloader
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from loguru import logger


def parse_args():
    parser = ArgumentParser(
        "Download reports published between start_date and end_date"
    )
    parser.add_argument("--start_date", type=str, default="2025-01-01")
    parser.add_argument("--end_date", type=str, default="2025-03-01")
    parser.add_argument(
        "--output_dir", type=str, default="edinet_corpus", help="Output directory"
    )
    parser.add_argument(
        "--doc_type",
        type=str,
        default="annual",
        help="Document type to download",
        choices=[
            "annual",
            "quarterly",
            "semiannual",
            "annual_amended",
            "quarterly_amended",
            "semiannual_amended",
        ],
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        default=8,
        help="Number of threads for parallel download",
    )
    return parser.parse_args()


def process_result(result, downloader, output_dir, doc_type) -> None:
    try:
        if downloader.get_doc_type(result.ordinanceCode, result.formCode) != doc_type:
            return

        if result.withdrawalStatus == "1":
            return
        edinet_code = result.edinetCode
        path = os.path.join(output_dir, doc_type, edinet_code)

        if os.path.exists(os.path.join(path, f"{result.docID}.json")):
            logger.info(f"Skip {edinet_code}: already exists")

        os.makedirs(path, exist_ok=True)

        downloader.download_document(result.docID, "tsv", path)
        downloader.download_document(result.docID, "pdf", path)

        with open(
            os.path.join(path, f"{result.docID}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=4)

        logger.info(f"Downloaded {result.docID} to {path}")
    except Exception as e:
        logger.error(f"Error processing {result.docID}: {e}")
        return None


if __name__ == "__main__":
    args = parse_args()
    downloader = Downloader()
    results = downloader.get_results(args.start_date, args.end_date)

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = [
            executor.submit(
                process_result, result, downloader, args.output_dir, args.doc_type
            )
            for result in results
        ]

        with tqdm(total=len(futures), desc="Downloading") as pbar:
            for future in as_completed(futures):
                result_msg = future.result()
                pbar.update(1)
