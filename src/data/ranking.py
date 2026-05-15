"""Coletor do Ranking de Reclamações do Banco Central do Brasil.

Baixa os arquivos CSV trimestrais publicados pelo DEATI/BCB, salva em
``data/raw/ranking/`` e fornece interface programática e CLI para reuso.

Endpoint: https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo
Formato retornado: CSV com separador ``;``, encoding ``latin-1``.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.utils.logger import get_logger

_URL_RANKING = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo"
_DIR_RAW = Path("data/raw/ranking")
_LOG_FILE = Path("data/logs/ranking_coleta.log")
_TIPO_PADRAO = "Bancos e financeiras"
_MIN_LINHAS_VALIDAS = 5

logger = get_logger(__name__, _LOG_FILE)


# ---------------------------------------------------------------------------
# Funções privadas
# ---------------------------------------------------------------------------


def _ultimo_trimestre_disponivel() -> tuple[int, int]:
    """Calcula o último trimestre provavelmente publicado pelo BCB.

    Usa a data atual menos um trimestre calendário. O fallback de tentar
    o anterior em caso de arquivo vazio acontece no loop de coleta em massa.

    Returns:
        Tupla ``(ano, trimestre)`` com o trimestre anterior ao atual.
    """
    agora = datetime.now()
    tri_atual = (agora.month - 1) // 3 + 1
    if tri_atual == 1:
        return agora.year - 1, 4
    return agora.year, tri_atual - 1


def _caminho_arquivo(ano: int, trimestre: int) -> Path:
    return _DIR_RAW / f"ranking_{ano}_T{trimestre}_bancos.csv"


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def _baixar_csv(ano: int, trimestre: int, tipo: str) -> bytes:
    """Faz a requisição HTTP e retorna o conteúdo binário do CSV."""
    params = {
        "ano": ano,
        "periodicidade": "TRIMESTRAL",
        "periodo": trimestre,
        "tipo": tipo,
    }
    resposta = requests.get(_URL_RANKING, params=params, timeout=30)
    resposta.raise_for_status()
    return resposta.content


def _csv_valido(caminho: Path) -> tuple[bool, Optional[int]]:
    """Tenta abrir o CSV e conta linhas. Retorna (valido, n_linhas).

    Args:
        caminho: Caminho do arquivo CSV a validar.

    Returns:
        Tupla ``(valido, n_linhas)``. ``n_linhas`` é ``None`` em caso de falha.
    """
    try:
        df = pd.read_csv(caminho, sep=";", encoding="latin-1", nrows=None)
        return len(df) >= _MIN_LINHAS_VALIDAS, len(df)
    except Exception:
        return False, None


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------


def coletar_trimestre(
    ano: int,
    trimestre: int,
    tipo: str = _TIPO_PADRAO,
) -> dict:
    """Coleta e persiste o CSV de um trimestre individual.

    Se o arquivo já existir em disco, retorna metadados com
    ``origem="cache"`` sem chamar a API.

    Args:
        ano: Ano de referência do ranking (ex.: 2024).
        trimestre: Trimestre de referência, entre 1 e 4.
        tipo: Segmento institucional. Default ``"Bancos e financeiras"``.

    Returns:
        Dict com metadados da operação (ano, trimestre, tipo, arquivo,
        linhas, origem, timestamp, status, erro).

    Raises:
        requests.RequestException: Após esgotar as 3 tentativas de retry.
        ValueError: Se ``trimestre`` estiver fora do intervalo 1–4.
    """
    if not 1 <= trimestre <= 4:
        raise ValueError(f"trimestre deve ser entre 1 e 4, recebeu: {trimestre}")

    caminho = _caminho_arquivo(ano, trimestre)
    timestamp = datetime.now().isoformat(timespec="seconds")

    meta_base: dict = {
        "ano": ano,
        "trimestre": trimestre,
        "tipo": tipo,
        "arquivo": caminho,
        "linhas": None,
        "origem": None,
        "timestamp": timestamp,
        "status": "sucesso",
        "erro": None,
    }

    # Cache hit
    if caminho.exists():
        valido, n_linhas = _csv_valido(caminho)
        if valido:
            logger.info(
                "Cache encontrado: %s T%s",
                ano,
                trimestre,
                extra={"ano": ano, "trimestre": trimestre, "status": "sucesso", "origem": "cache", "erro": None},
            )
            return {**meta_base, "linhas": n_linhas, "origem": "cache"}
        # Arquivo corrompido em cache — deleta e baixa novamente
        caminho.unlink()
        logger.warning("Arquivo corrompido removido: %s", caminho.name)

    # Download
    try:
        conteudo = _baixar_csv(ano, trimestre, tipo)
    except requests.RequestException as exc:
        erro = f"Falha na requisição após retries: {exc}"
        logger.error(
            "Falha ao baixar %s T%s: %s",
            ano,
            trimestre,
            erro,
            extra={"ano": ano, "trimestre": trimestre, "status": "falha", "origem": "api", "erro": erro},
        )
        raise

    _DIR_RAW.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)

    valido, n_linhas = _csv_valido(caminho)

    if not valido:
        caminho.unlink(missing_ok=True)
        erro = "Trimestre não publicado ou arquivo vazio (< 5 linhas)"
        logger.warning(
            "%s T%s: %s",
            ano,
            trimestre,
            erro,
            extra={"ano": ano, "trimestre": trimestre, "status": "falha", "origem": "api", "erro": erro},
        )
        return {**meta_base, "linhas": n_linhas, "origem": "api", "status": "falha", "erro": erro}

    logger.info(
        "Baixado: %s T%s (%s linhas)",
        ano,
        trimestre,
        n_linhas,
        extra={"ano": ano, "trimestre": trimestre, "status": "sucesso", "origem": "api", "erro": None},
    )
    return {**meta_base, "linhas": n_linhas, "origem": "api"}


def coletar_historico(
    ano_inicio: int = 2023,
    tri_inicio: int = 1,
    ano_fim: Optional[int] = None,
    tri_fim: Optional[int] = None,
    tipo: str = _TIPO_PADRAO,
) -> list[dict]:
    """Coleta todos os trimestres entre os limites informados.

    O limite superior é calculado dinamicamente se não informado (trimestre
    atual menos 1). Se esse trimestre vier vazio, tenta o anterior como
    fallback.

    Args:
        ano_inicio: Ano inicial. Default 2023.
        tri_inicio: Trimestre inicial. Default 1.
        ano_fim: Ano final. Calculado dinamicamente se omitido.
        tri_fim: Trimestre final. Calculado dinamicamente se omitido.
        tipo: Segmento institucional. Default ``"Bancos e financeiras"``.

    Returns:
        Lista de dicts de metadados, um por trimestre (incluindo falhas).
    """
    limite_dinamico = ano_fim is None or tri_fim is None
    if limite_dinamico:
        ano_fim, tri_fim = _ultimo_trimestre_disponivel()

    pares = _gerar_pares(ano_inicio, tri_inicio, ano_fim, tri_fim)

    # Fallback: se o limite foi calculado dinamicamente e o último trimestre
    # ainda não foi publicado, remove-o da lista e tenta o anterior
    if limite_dinamico and pares:
        ultimo = pares[-1]
        meta_teste = _tentar_sem_raise(ultimo[0], ultimo[1], tipo)
        if meta_teste["status"] == "falha" and "não publicado" in (meta_teste["erro"] or ""):
            pares = pares[:-1]
        else:
            # Resultado do fallback já é válido — inclui direto, pula no loop
            resultados: list[dict] = [meta_teste]
            for ano, tri in pares[:-1]:
                resultados.append(_tentar_sem_raise(ano, tri, tipo))
            _imprimir_sumario(resultados)
            return resultados

    resultados = [_tentar_sem_raise(ano, tri, tipo) for ano, tri in pares]
    _imprimir_sumario(resultados)
    return resultados


def _gerar_pares(
    ano_inicio: int,
    tri_inicio: int,
    ano_fim: int,
    tri_fim: int,
) -> list[tuple[int, int]]:
    """Gera lista ordenada de pares (ano, trimestre) no intervalo."""
    pares = []
    ano, tri = ano_inicio, tri_inicio
    while (ano, tri) <= (ano_fim, tri_fim):
        pares.append((ano, tri))
        if tri == 4:
            ano, tri = ano + 1, 1
        else:
            tri += 1
    return pares


def _tentar_sem_raise(ano: int, trimestre: int, tipo: str) -> Optional[dict]:
    """Chama ``coletar_trimestre`` absorvendo exceções (para uso em modo massa)."""
    try:
        return coletar_trimestre(ano, trimestre, tipo)
    except Exception as exc:
        erro = str(exc)
        logger.warning(
            "Erro não recuperável em %s T%s: %s",
            ano,
            trimestre,
            erro,
            extra={"ano": ano, "trimestre": trimestre, "status": "falha", "origem": "api", "erro": erro},
        )
        return {
            "ano": ano,
            "trimestre": trimestre,
            "tipo": tipo,
            "arquivo": _caminho_arquivo(ano, trimestre),
            "linhas": None,
            "origem": "api",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": "falha",
            "erro": erro,
        }


def _imprimir_sumario(resultados: list[dict]) -> None:
    sucesso = sum(1 for r in resultados if r["status"] == "sucesso")
    falhas = len(resultados) - sucesso
    print(f"\n[OK] {sucesso} trimestres baixados com sucesso", end="")
    if falhas:
        print(f" | [FALHA] {falhas} trimestres falharam")
        print("Detalhes em data/logs/ranking_coleta.log")
    else:
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_periodo(valor: str) -> tuple[int, int]:
    """Converte string ``YYYYQN`` em tupla ``(ano, trimestre)``.

    Args:
        valor: String no formato ``YYYYQN``, ex.: ``2024Q3``.

    Returns:
        Tupla ``(ano, trimestre)``.

    Raises:
        argparse.ArgumentTypeError: Se o formato for inválido.
    """
    try:
        partes = valor.upper().split("Q")
        if len(partes) != 2:
            raise ValueError
        ano, tri = int(partes[0]), int(partes[1])
        if not 1 <= tri <= 4:
            raise ValueError
        return ano, tri
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Formato inválido: '{valor}'. Use YYYYQN, ex.: 2024Q3"
        )


def main(argv: Optional[list[str]] = None) -> None:
    """Ponto de entrada da CLI."""
    parser = argparse.ArgumentParser(
        description="Coletor do Ranking de Reclamações do BCB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python -m src.data.ranking --ano 2024 --tri 3\n"
            "  python -m src.data.ranking --massa\n"
            "  python -m src.data.ranking --massa --inicio 2024Q1 --fim 2025Q4"
        ),
    )

    parser.add_argument("--ano", type=int, help="Ano do trimestre (modo individual)")
    parser.add_argument("--tri", type=int, help="Trimestre 1–4 (modo individual)")
    parser.add_argument("--massa", action="store_true", help="Coleta histórico completo")
    parser.add_argument("--inicio", type=_parse_periodo, metavar="YYYYQN", help="Início do período em massa")
    parser.add_argument("--fim", type=_parse_periodo, metavar="YYYYQN", help="Fim do período em massa")
    parser.add_argument(
        "--tipo",
        default=_TIPO_PADRAO,
        help=f'Segmento (default: "{_TIPO_PADRAO}")',
    )

    args = parser.parse_args(argv)

    if args.massa:
        kwargs: dict = {"tipo": args.tipo}
        if args.inicio:
            kwargs["ano_inicio"], kwargs["tri_inicio"] = args.inicio
        if args.fim:
            kwargs["ano_fim"], kwargs["tri_fim"] = args.fim
        coletar_historico(**kwargs)
        sys.exit(0)

    if args.ano is None or args.tri is None:
        parser.error("Informe --ano e --tri para coleta individual, ou use --massa.")

    try:
        meta = coletar_trimestre(args.ano, args.tri, args.tipo)
        origem = meta["origem"]
        linhas = meta["linhas"]
        print(f"Status: {meta['status']} | origem: {origem} | linhas: {linhas}")
        sys.exit(0)
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
