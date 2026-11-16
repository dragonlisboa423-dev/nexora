/** Error pages from forwarding proxies are not successful JSON uploads. */
export function uploadResponse(raw: string, status: number, contentType = "") {
  let data: any;
  try {
    data = JSON.parse(raw);
  } catch {
    if (status === 413)
      throw new Error(
        "HTTP 413: o servidor ou proxy recusou o tamanho do envio. Confira o limite do Centro Smolin.",
      );
    throw new Error(
      `O servidor/proxy devolveu ${contentType.includes("html") ? "HTML" : "uma resposta inválida"} (HTTP ${status}), em vez de confirmar o arquivo. Confira a sessão da SALY e tente novamente.`,
    );
  }
  if (status < 200 || status >= 300)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Envio recusado (HTTP ${status}).`,
    );
  if (!data || typeof data !== "object")
    throw new Error("O servidor não confirmou o recebimento.");
  return data;
}

export function smolinError(error: unknown): string {
  return error instanceof SyntaxError
    ? "O servidor/proxy respondeu em formato inesperado. Confira sua sessão da SALY e tente novamente."
    : error instanceof Error
      ? error.message
      : "Não foi possível confirmar a operação.";
}
