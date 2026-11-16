import { Link } from "react-router-dom";

export function OfflinePanel() {
  return (
    <section className="card">
      <h2>Dados privados neste dispositivo</h2>
      <p>
        Prepare um cofre opcional no navegador para consultar e editar memórias
        e lembretes sem rede, além de guardar documentos escolhidos. O conteúdo
        fica criptografado com uma senha local. A chave Groq e a senha de acesso
        não são copiadas.
      </p>
      <p>
        Alterações ficam pendentes até sincronização autenticada; conflitos são
        revisados. Uma interface em cache não fornece IA offline.
      </p>
      <Link className="citation" to="/offline">
        Abrir ou preparar cofre local →
      </Link>
    </section>
  );
}
