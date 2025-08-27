import os

class LocalFileExplorer:
    def __init__(self):
        pass  # Sin configuración inicial

    def _get_tree(self, directory, prefix="") -> list:
        tree = []
        try:
            entries = sorted(os.listdir(directory))
            entries = [e for e in entries if not e.startswith(".")]
        except Exception as e:
            return [f"Error reading directory: {e}"]

        for idx, entry in enumerate(entries):
            path = os.path.join(directory, entry)
            is_last = idx == len(entries) - 1
            branch = "└── " if is_last else "├── "
            subprefix = "    " if is_last else "│   "
            tree.append(f"{prefix}{branch}{entry}")
            if os.path.isdir(path):
                tree.extend(self._get_tree(path, prefix + subprefix))
        return tree

    def _find_project_root(self, current_path: str) -> str:
        abs_path = os.path.abspath(current_path)
        if os.path.isfile(abs_path):
            return os.path.dirname(abs_path)
        if os.path.isdir(abs_path):
            return abs_path
        raise ValueError(f"Path inválido o inexistente: {abs_path}")

    def list_directory_tree(self, working_path: str) -> str:
        try:
            project_root = self._find_project_root(working_path)
        except ValueError as e:
            return str(e)

        tree = self._get_tree(project_root)
        return f"📂 Directory structure of `{project_root}`:\n\n" + "\n".join(tree)
