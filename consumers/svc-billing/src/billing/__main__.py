"""``python -m billing`` entry point."""

import sys

from billing.interfaces.cli import main

sys.exit(main())
