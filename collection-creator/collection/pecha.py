import csv
from pathlib import Path
from typing import List

from collection.collection import Collection
from views.view import View


class PechaCollection(Collection):

    def __init__(self, title:str, items, views:List[View], parent_dir: Path, id=None) -> None:
        super().__init__(
            title=title,
            items=items,
            views=views,
            parent_dir=parent_dir,
            id=id
            )

    def save_readme(self):
        readme = f"""
        ID: {self.id}
        Title: {self.title}
        Number of Pecha: {len(self.items)}

        """
        (self.collection_dir / "ReadMe.md").write_text(readme, encoding="utf-8")
