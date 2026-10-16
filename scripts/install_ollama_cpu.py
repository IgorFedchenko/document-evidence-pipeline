"""Stream a pinned official Ollama archive; retain CPU files, verify the complete SHA-256."""

import hashlib
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

VERSION = "0.12.3"
# Filled from the official release's sha256sum.txt, never discovered dynamically during the build.
HASHES = {
    "arm64": "d0cc8332edd26778b4c05e1b1d1b5d09f5f5611ad6a939fac4a9da6b5cb81d90",
    "amd64": "649ac33e3e22304f650207e4f6379dbc2c2397d840593caf5bba6605c2886229",
}


class HashedStream:
    def __init__(self, source):
        self.source = source
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        chunk = self.source.read(size)
        self.digest.update(chunk)
        return chunk


def main():
    architecture = sys.argv[1]
    expected = HASHES[architecture]
    url = f"https://github.com/ollama/ollama/releases/download/v{VERSION}/ollama-linux-{architecture}.tgz"
    with urllib.request.urlopen(url, timeout=120) as response:
        stream = HashedStream(response)
        with tarfile.open(fileobj=stream, mode="r|gz") as archive:
            for member in archive:
                path = Path(member.name)
                if path.is_absolute() or ".." in path.parts or not member.isfile():
                    continue
                keep = str(path) == "bin/ollama" or (
                    path.parent == Path("lib/ollama") and path.name.startswith("libggml")
                )
                if keep:
                    target = Path("/usr") / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(0o755)
                    print(f"Installed {path}", flush=True)
        while stream.read(1024 * 1024):
            pass
        if stream.digest.hexdigest() != expected:
            raise RuntimeError("Official Ollama archive SHA-256 mismatch")
    print(f"Verified Ollama {VERSION} {architecture}; GPU libraries excluded")


if __name__ == "__main__":
    main()
