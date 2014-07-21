import collections


def flatten(dictionary, parent_key='', sep='.'):
    """
    Flatten dictionary

    http://stackoverflow.com/a/6027615
    """
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(value, collections.MutableMapping):
            items.extend(flatten(value, new_key).items())
        else:
            items.append((new_key, value))
    return dict(items)
