"""Exceções de domínio. A camada de API as traduz para códigos HTTP."""


class DomainError(Exception):
    """Base para todos os erros de negócio."""


class InvalidImageError(DomainError):
    """O conteúdo enviado não é uma imagem válida/decodificável."""


class DetectorUnavailableError(DomainError):
    """O modelo Haar Cascade não foi encontrado ou não pôde ser carregado."""


class InspectionNotFoundError(DomainError):
    """Inspeção solicitada não existe."""
