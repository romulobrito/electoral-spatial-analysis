"""Official TSE resource locations verified from portal on 2026-10-17."""
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class OfficialResource:
    key: str
    year: int
    kind: str
    url: str
    dataset: str
    resource_id: str | None = None


TSE_BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
RESOURCES = {
    "president_2022": OfficialResource("president_2022", 2022, "votes_by_section",
        f"{TSE_BASE}/votacao_secao/votacao_secao_2022_BR.zip",
        "https://dadosabertos.tse.jus.br/dataset/resultados-2022",
        "f509562b-3b7f-487d-ad61-145a7ae6b96f"),
    "president_2026": OfficialResource("president_2026", 2026, "votes_by_section",
        f"{TSE_BASE}/votacao_secao/votacao_secao_2026_BR.zip",
        "https://dadosabertos.tse.jus.br/dataset/resultados-2026",
        "01ea4ccd-f443-469c-9f29-c69ff97f7d4c"),
    "turnout_2022": OfficialResource("turnout_2022", 2022, "detail_by_section",
        f"{TSE_BASE}/detalhe_votacao_secao/detalhe_votacao_secao_2022.zip",
        "https://dadosabertos.tse.jus.br/dataset/resultados-2022"),
    "turnout_2026": OfficialResource("turnout_2026", 2026, "detail_by_section",
        f"{TSE_BASE}/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip",
        "https://dadosabertos.tse.jus.br/dataset/resultados-2026"),
}


def resource_manifest() -> list[dict]:
    return [asdict(resource) for resource in RESOURCES.values()]


def validated_download_url(resource: OfficialResource) -> str:
    parsed = urlsplit(resource.url)
    if (parsed.scheme, parsed.hostname, parsed.port) != ("https", "cdn.tse.jus.br", None):
        raise ValueError("Resource host is not an approved official TSE host")
    if not parsed.path.startswith("/estatistica/sead/odsele/") or not parsed.path.endswith(".zip"):
        raise ValueError("Resource path is outside expected official TSE directory")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Unexpected resource URL components")
    return resource.url
