export function chatFailure(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  if (error instanceof SyntaxError)
    return "O servidor ou o encaminhamento devolveu uma resposta inválida ou incompleta. Abra a SALY novamente pelo Codespace, verifique sua sessão e reabra a conversa antes de reenviar.";
  if (
    /network\s?error|failed to fetch|fetch failed|load failed|network request failed|terminated|connection.*(closed|reset)/i.test(
      message,
    )
  )
    return "A conexão com a SALY foi interrompida antes de confirmar a resposta. Confira se o Codespace e a SALY continuam ligados. Reabra a conversa antes de reenviar, para evitar duplicações.";
  return message;
}
export async function chatHttpFailure(response: Response) {
  const body = await response.json().catch(() => null);
  if (typeof body?.detail === "string") return body.detail;
  if ([502, 503, 504].includes(response.status))
    return `O servidor ou o encaminhamento do Codespace não respondeu (HTTP ${response.status}). Confira se a SALY e o Ollama continuam ligados e reabra a conversa antes de reenviar.`;
  if ([401, 403].includes(response.status))
    return "A sessão privada expirou ou foi recusada. Entre novamente antes de conversar.";
  return `Não foi possível iniciar a resposta (HTTP ${response.status}).`;
}
