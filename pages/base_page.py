"""Base page class for Streamlit pages."""


class Page:
    """Base class for Streamlit page components."""

    def page(self):
        """Override this method to render page content."""
        raise NotImplementedError()
