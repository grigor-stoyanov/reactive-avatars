# Build a double-clickable binary for the OS you're on (PyInstaller can't cross-compile).
# Windows builds come from CI: see .github/workflows/release.yml
.PHONY: run build test clean

run:
	uv run reactive-avatars

test:
	uv run --group dev pytest -q

build:
	uv run --with pyinstaller pyinstaller --noconfirm --clean \
		--distpath dist --workpath build/pyinstaller packaging/reactive-avatars.spec
	@echo "Built: dist/reactive-avatars"

clean:
	rm -rf build dist
