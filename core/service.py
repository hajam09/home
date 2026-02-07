from core.models import EnergyPayment


def mapChannelForEnergyPayment(label):
    if label is None:
        return None
    for choice in EnergyPayment.Channel:

        if choice.label.lower() == label.lower():
            return choice.value

    raise ValueError('Invalid channel')
