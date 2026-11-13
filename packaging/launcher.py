"""PyInstaller entry point (the package itself uses relative imports)."""
import multiprocessing

from reactive_avatars import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
