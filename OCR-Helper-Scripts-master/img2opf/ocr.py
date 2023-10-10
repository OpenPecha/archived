import io
import json
from pathlib import Path

from google.cloud import vision
from google.cloud.vision import AnnotateImageResponse

vision_client = vision.ImageAnnotatorClient()


def google_ocr(image, lang_hint=None):
    """
    image: file_path or image bytes
    return: google ocr response in Json
    """
    if isinstance(image, (str, Path)):
        with io.open(image, "rb") as image_file:
            content = image_file.read()
    else:
        content = image
    ocr_image = vision.Image(content=content)

    features = [
        {
            "type_": vision.Feature.Type.DOCUMENT_TEXT_DETECTION,
            "model": "builtin/weekly",
        }
    ]

    image_context = {}
    if lang_hint:
        image_context["language_hints"] = [lang_hint]

    response = vision_client.annotate_image(
        {"image": ocr_image, "features": features, "image_context": image_context}
    )

    response_json = AnnotateImageResponse.to_json(response)
    response = json.loads(response_json)

    return response


if __name__ == "__main__":

    import argparse

    from tqdm import tqdm

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input_dir", type=str, help="directory path containing all the images"
    )
    ap.add_argument("--n", type=int, help="start page number", default=1)
    ap.add_argument(
        "--output_dir", default="./output", help="directory to store the ocr output"
    )
    ap.add_argument(
        "--combine",
        action="store_true",
        help="Combine the output of all the images in output_dir",
    )
    ap.add_argument(
        "--save-json",
        action="store_true",
        help="Save OCR output in json",
    )
    ap.add_argument("--lang", type=str, help="langauge code of the document")
    args = ap.parse_args()

    print("[INFO] OCR started ....")
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    fns = [fn for fn in input_path.iterdir() if fn.suffix in [".png", ".jpg", ".jpeg"]]
    if args.combine:
        fns = sorted(fns)

    texts = []
    for fn in tqdm(fns[args.n - 1 :]):
        response = google_ocr(fn, lang_hint=args.lang)
        if "textAnnotations" not in response:
            continue
        text = response["textAnnotations"][0]["description"]

        if args.save_json:
            json_output_fn = output_path / f"{fn.stem}.json"
            json.dump(response, json_output_fn.open("w"))

        if not args.combine:
            output_fn = output_path / f"{fn.stem}.txt"
            output_fn.write_text(text)
        else:
            texts.append(text)

    if args.combine and texts:
        output_fn = output_path / f"{input_path.name}.txt"
        output_fn.write_text("\n\n\n".join(texts))
        print("[INFO] Output is saved at:", str(output_fn))
    else:
        print("INFO]  Output is saved at:", str(output_path))
