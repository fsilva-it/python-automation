from pathlib import Path

def organize_txt_files(folder_path: str) -> None:
    """
    Rename all .txt files in the given folder by adding a prefix.
    """
    folder = Path(folder_path)

    for file in folder.glob("*.txt"):
        new_name = folder / f"txt_{file.name}"
        file.rename(new_name)


if __name__ == "__main__":
    organize_txt_files("files")
