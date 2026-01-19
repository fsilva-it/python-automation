from pathlib import Path

def change_extension(folder_path: str, old_ext: str, new_ext: str) -> None:
    """
    Change file extensions inside a folder.
    """
    folder = Path(folder_path)

    for file in folder.glob(f"*.{old_ext}"):
        file.rename(file.with_suffix(f".{new_ext}"))


if __name__ == "__main__":
    change_extension("files", "log", "txt")
