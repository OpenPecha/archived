from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, redirect, request, url_for
from openpecha.catalog import CatalogManager
from openpecha.formatters import HFMLFormatter

from .models import Pecha

blueprint = Blueprint("pecha", __name__, url_prefix="/pecha", static_folder="../static")


def validate_img_extension(fn):
    fn = Path(fn)
    if fn.suffix not in current_app.config["UPLOAD_EXTENSIONS"]:
        abort(400)
    return fn.name


def save_image(parents_dir, file_obj):
    filename = validate_img_extension(file_obj.filename)
    base_dir = current_app.config["BOOK_ASSETS_UPLOAD_PATH"] / parents_dir
    base_dir.mkdir(exist_ok=True, parents=True)
    file_path = base_dir / filename
    file_obj.save(file_path)
    return filename


def parser_authors(string):
    delimeter = " "
    if "," in string:
        delimeter = ","
    return [author.strip() for author in string.split(delimeter)]


def create_soruce_metadata(request):
    title = request.form.get("title")
    subtitle = request.form.get("sub-title")
    authors = request.form.get("author")
    collection_title = request.form.get("collection-title")
    publisher = request.form.get("publisher")
    id_ = request.form.get("sku")
    front_cover_image = request.files.get("front-cover-image")
    publication_data_image = request.files.get("publication-data-image")
    content_images = request.files.getlist("content-images")

    # save images
    assets_path = "assets/images"
    pecha_images_path = f"{id_}/{assets_path}"
    pecha_content_images_path = f"{pecha_images_path}/content"
    front_cover_image_fn = save_image(pecha_images_path, front_cover_image)
    publication_data_image_fn = save_image(pecha_images_path, publication_data_image)
    for content_image in content_images:
        save_image(pecha_content_images_path, content_image)

    metadata = {
        "id": id_.strip(),
        "title": title.strip(),
        "subtitle": subtitle.strip(),
        "author": authors,
        "collection-title": collection_title.strip(),
        "publisher": publisher.strip(),
        "images": {
            "front-cover-image": f"{assets_path}/{front_cover_image_fn}",
            "publication-data-image": f"{assets_path}/{publication_data_image_fn}",
            "content-images-path": f"{assets_path}/content",
        },
    }

    return metadata


def save_text(parents_dir, text):
    base_dir = current_app.config["BOOK_ASSETS_UPLOAD_PATH"] / parents_dir
    base_dir.mkdir(exist_ok=True, parents=True)
    text_fn = base_dir / "v001.txt"
    text_fn.write_text(text)
    return text_fn.parent


@blueprint.route("/create", methods=["POST"])
def create_pecha():
    source_metadata = create_soruce_metadata(request)
    text_path = save_text(
        f"{source_metadata['id']}/text", request.form.get("content-text")
    )
    layers = [
        "book-title",
        "chapter-title",
        "author",
        "cition",
        "sabche",
        "root-verse",
        "foot-note",
        "all",
    ]
    catalog = CatalogManager(
        formatter=HFMLFormatter(
            metadata={"source_metadata": source_metadata, "layers": layers}
        ),
        layers=layers,
        token=current_app.config["GITHUB_TOKEN"],
    )
    catalog.add_hfml_item(text_path)
    catalog.update()
    pecha_id = f"P{catalog.last_id:06}"
    return redirect(url_for("main.editor", pecha_id=pecha_id))


@blueprint.route("/secret", methods=["POST"])
def create_secret():
    for i in range(100, 101):
        pecha_id = f"P{i:06}"
        pecha = Pecha.query.filter_by(id=pecha_id).first()
        if pecha:
            continue
        Pecha.create(id=pecha_id, secret_key=uuid4().hex)
        print(f"added {pecha_id}")
    return redirect(url_for("user.admin_dashboard"))

    # pecha_id = request.form.get("pecha-id")
    # if pecha_id and not pecha_id.startswith(PECHA_PREFIX):
    #     flash(f"{pecha_id} is in valid", "danger")
    # pecha = Pecha.create(id=pecha_id, secret_key=uuid4().hex)
    # if pecha:
    #     flash(f"Secret Key successfully created for {pecha.id}", "success")
