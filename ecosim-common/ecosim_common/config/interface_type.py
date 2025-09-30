from enum import Enum


class InterfaceType(str, Enum):
    INPUT = 'input'
    OUTPUT = 'output'

    @staticmethod
    def of(interface_type: str) -> 'InterfaceType':
        if interface_type.lower() == 'input':
            return InterfaceType.INPUT
        if interface_type.lower() == 'output':
            return InterfaceType.OUTPUT
        raise ValueError(f'Type {interface_type} not known')
