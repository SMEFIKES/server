class Choices:
    @classmethod
    def choices(cls):
        return [
            value
            for name, value in cls.__dict__.items()
            if isinstance(value, str) and not name.startswith('_')
        ]
