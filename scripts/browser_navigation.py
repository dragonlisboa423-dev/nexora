"""Exercise SALY 2.0's four areas rather than its retired flat sidebar."""

import re

AREAS = {
    "Memórias": ("Conhecimento", "Memórias"),
    "Centro Smolin": ("Conhecimento", "Centro Smolin"),
    "Biblioteca": ("Conhecimento", "Biblioteca"),
    "Espaço": ("Conhecimento", "Espaço"),
    "Compras": ("Rotina", "Compras"),
    "Agenda": ("Rotina", "Agenda"),
    "Alarmes": ("Rotina", "Alarmes"),
    "Estúdio Multimídia": ("Mídia", None),
}


def go(page, label):
    if label in AREAS:
        area, child = AREAS[label]
        mobile = page.get_by_role("navigation", name="Navegação móvel", exact=True)
        if mobile.is_visible() and page.locator(".sidebar.open").is_visible():
            page.get_by_role("button", name="Fechar menu", exact=True).click(
                position={"x": page.viewport_size["width"] - 20, "y": 100}
            )
        primary = (
            mobile
            if mobile.is_visible()
            else page.get_by_role("navigation", name="Áreas principais", exact=True)
        )
        primary.get_by_role("link", name=area, exact=True).click()
        if child:
            page.get_by_role("navigation", name="Navegação de " + area, exact=True).get_by_role(
                "link", name=child, exact=True
            ).click()
    else:
        settings = page.get_by_role("link", name="Ajustes e recursos", exact=True)
        if not settings.is_visible():
            page.get_by_role("button", name="Alternar menu", exact=True).click()
        settings.click()
        titles = {
            "Ferramentas e integrações": "Ferramentas e integrações",
            "Biblioteca de vozes": "Voz e escuta",
            "Laboratório SALY": "Laboratório SALY",
            "Avaliação": "Avaliação",
            "Configurações": "Preferências",
            "Atividades": "Atividades",
        }
        if label == "Atividades":
            page.goto(page.url.split("/advanced")[0] + "/activity")
        else:
            page.get_by_role("link", name=re.compile("^" + re.escape(titles[label]))).first.click()
