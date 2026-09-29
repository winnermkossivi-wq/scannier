"""
Exception personnalisee pour comptes suspendus.
"""
class CompteSuspendu(Exception):
    """Levee quand un marchand/employe tente d'agir alors que son compte est suspendu."""
    pass