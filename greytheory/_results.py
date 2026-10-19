"""Readable result names backed by the existing fitted state."""


def result_alias(attribute, description):
    """Expose one result under another name without storing a second copy."""
    def get(instance):
        return getattr(instance, attribute)

    def set_value(instance, value):
        setattr(instance, attribute, value)

    def delete(instance):
        delattr(instance, attribute)

    return property(get, set_value, delete, description)
