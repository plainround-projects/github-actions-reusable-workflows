"""``python -m orders`` entry point."""

import sys

from orders.interfaces.cli import main

sys.exit(main())
