import os
import sys

dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if dir_name not in sys.path:
    sys.path.append(dir_name)

import streamlit as st
import os
import json
import requests
from functools import partial


class Connector:
    """Typical commector to"""

    BASE_URL = os.environ.get("API_BASE_URL", "")

    HEADERS_JSON = {"content-type": "application/json"}

    @property
    def token(self):
        return

    # @st.cache(ttl=60)
    def get_something(
        self,
    ):
        results = []
        return results


class Page:
    connector = Connector()

    def page(self):
        """Override this method to display page items."""
        raise NotImplementedError()
