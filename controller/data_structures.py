from collections.abc import MutableSet


class CaseInsensitiveSet(MutableSet):
    def __init__(self, iterable=None):
        self._data = {}
        if iterable is not None:
            for item in iterable:
                self.add(item)

    def add(self, item):
        self._data[item.lower()] = item

    def discard(self, item):
        self._data.pop(item.lower(), None)

    def __contains__(self, item):
        return item.lower() in self._data

    def __iter__(self):
        return iter(self._data.values())

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"{{{', '.join(repr(v) for v in self._data.values())}}}"

    def intersection(self, other):
        """Return intersection preserving THIS set's casing"""
        if isinstance(other, CaseInsensitiveSet):
            other_lower = set(other._data.keys())
        else:
            other_lower = {item.lower() for item in other}

        result = CaseInsensitiveSet()
        for lower_key, original in self._data.items():
            if lower_key in other_lower:
                result.add(original)
        return result

    def union(self, other):
        result = CaseInsensitiveSet(self._data.values())
        for item in other:
            result.add(item)
        return result

    def difference(self, other):
        if isinstance(other, CaseInsensitiveSet):
            other_lower = set(other._data.keys())
        else:
            other_lower = {item.lower() for item in other}

        result = CaseInsensitiveSet()
        for lower_key, original in self._data.items():
            if lower_key not in other_lower:
                result.add(original)
        return result
