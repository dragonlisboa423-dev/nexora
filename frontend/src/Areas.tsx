import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  BookOpen,
  Brain,
  CalendarDays,
  Database,
  FolderOpen,
  Leaf,
  ShoppingBag,
  Bell,
  SlidersHorizontal,
  Mic,
  ShieldCheck,
  Wrench,
  Activity,
  FlaskConical,
  HardDrive,
  Film,
} from "lucide-react";
import { api } from "./api";

type Data = Record<string, any>;
function AreaIntro({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <header className="area-intro">
      <span className="eyebrow">
        <Leaf size={13} />
        {eyebrow}
      </span>
      <h1>{title}</h1>
      <p>{children}</p>
    </header>
  );
}
function Destination({
  to,
  icon: Icon,
  title,
  description,
  detail,
  className = "",
}: {
  to: string;
  icon: typeof Leaf;
  title: string;
  description: string;
  detail?: string;
  className?: string;
}) {
  return (
    <Link to={to} className={`destination-card ${className}`}>
      <span className="destination-icon">
        <Icon size={24} strokeWidth={1.2} />
      </span>
      <ArrowUpRight className="destination-arrow" size={18} />
      <h2>{title}</h2>
      <p>{description}</p>
      {detail && <small>{detail}</small>}
    </Link>
  );
}
export function KnowledgeHome() {
  const [data, setData] = useState<{
      memories?: Data[];
      documents?: Data[];
      books?: Data[];
    }>({}),
    [warning, setWarning] = useState(false);
  useEffect(() => {
    let alive = true;
    Promise.allSettled([
      api("/memories"),
      api("/knowledge"),
      api("/books"),
    ]).then((results) => {
      if (!alive) return;
      setData(
        Object.fromEntries(
          results.flatMap((r, i) =>
            r.status === "fulfilled"
              ? [[["memories", "documents", "books"][i], r.value]]
              : [],
          ),
        ),
      );
      setWarning(results.some((r) => r.status === "rejected"));
    });
    return () => {
      alive = false;
    };
  }, []);
  return (
    <div className="area-home knowledge-home">
      <AreaIntro eyebrow="CONHECIMENTO" title="Centro Memorial">
        O que você vive. O que você aprende. Cada coisa em seu lugar.
      </AreaIntro>
      {warning && (
        <p role="status">
          Parte do acervo não pôde ser consultada. Os acessos abaixo continuam
          disponíveis.
        </p>
      )}
      <div className="destination-grid">
        <Destination
          to="/memory"
          icon={Brain}
          title="Memórias pessoais"
          description="Preferências, ideias e informações que você escolheu guardar."
          detail={
            data.memories
              ? `${data.memories.length} memórias sob seu controle`
              : "Consultar memórias"
          }
          className="memory-destination"
        />
        <Destination
          to="/knowledge/documents"
          icon={Database}
          title="Centro Smolin"
          description="Seus documentos originais, pesquisa e referências com origem."
          detail={
            data.documents
              ? `${data.documents.length} arquivos no acervo`
              : "Consultar documentos"
          }
          className="smolin-destination"
        />
        <Destination
          to="/library"
          icon={BookOpen}
          title="Biblioteca"
          description="Abra um livro. Explore uma página. Continue de onde parou."
          detail={
            data.books
              ? `${data.books.length} livros disponíveis para leitura`
              : "Explorar livros"
          }
          className="library-destination"
        />
        <Destination
          to="/space"
          icon={FolderOpen}
          title="Espaço pessoal"
          description="Gavetas, links e referências que merecem um lugar próprio."
          detail="Organizar referências"
        />
      </div>
      {data.books?.[0] && (
        <section className="knowledge-reading">
          <div
            className="book-miniature"
            style={{ background: data.books[0].cover_color }}
          >
            <Leaf size={34} strokeWidth={1} />
            <span>{data.books[0].subject}</span>
          </div>
          <div>
            <small>NA SUA ESTANTE</small>
            <h2>{data.books[0].title}</h2>
            <p>{data.books[0].subtitle}</p>
            <Link className="file-button" to="/library">
              Abrir a Biblioteca <ArrowUpRight size={15} />
            </Link>
          </div>
        </section>
      )}
      <div className="area-note">
        <ShieldCheck size={16} />
        <p>
          Memórias pessoais e fontes documentais permanecem distintas. Você
          decide o que guardar, utilizar ou excluir.
        </p>
        <Link to="/settings/personality">Preferências persistentes ↗</Link>
      </div>
    </div>
  );
}
export function RoutineHome() {
  const month = new Date().toLocaleDateString("sv-SE").slice(0, 7);
  const [data, setData] = useState<{
    summary?: Data;
    reminders?: Data[];
    alarms?: Data[];
  }>({});
  useEffect(() => {
    let alive = true;
    Promise.allSettled([
      api(`/purchases-summary?month=${month}`),
      api("/reminders"),
      api("/alarms"),
    ]).then((results) => {
      if (alive)
        setData(
          Object.fromEntries(
            results.flatMap((r, i) =>
              r.status === "fulfilled"
                ? [[["summary", "reminders", "alarms"][i], r.value]]
                : [],
            ),
          ),
        );
    });
    return () => {
      alive = false;
    };
  }, [month]);
  const pending = data.reminders?.filter((r) => !r.done) ?? [],
    active = data.alarms?.filter((a) => a.enabled) ?? [];
  const money = (n: number) =>
    (n / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  return (
    <div className="area-home routine-home">
      <AreaIntro eyebrow="ROTINA" title="Espaço para o seu dia.">
        Planeje com calma. Cuide do que importa.
      </AreaIntro>
      <div className="routine-overview">
        <section className="card">
          <small>SEU PLANEJAMENTO</small>
          <strong>{data.reminders ? pending.length : "—"}</strong>
          <p>lembretes em aberto</p>
          <Link to="/agenda">Ver agenda ↗</Link>
        </section>
        <section className="card">
          <small>NESTE MÊS</small>
          <strong>
            {data.summary ? money(data.summary.total_cents) : "—"}
          </strong>
          <p>em compras registradas</p>
          <Link to="/purchases">Acompanhar orçamento ↗</Link>
        </section>
        <section className="card">
          <small>NO SEU RITMO</small>
          <strong>{data.alarms ? active.length : "—"}</strong>
          <p>alarmes habilitados</p>
          <Link to="/alarms">Ajustar lembretes ↗</Link>
        </section>
      </div>
      <div className="destination-grid">
        <Destination
          to="/agenda"
          icon={CalendarDays}
          title="Agenda"
          description="Compromissos, planos e espaço entre uma coisa e outra."
        />
        <Destination
          to="/purchases"
          icon={ShoppingBag}
          title="Compras e desejos"
          description="Uma visão do que você quer, do que já chegou e do seu orçamento."
        />
        <Destination
          to="/alarms"
          icon={Bell}
          title="Alarmes"
          description="Lembretes no momento certo, com os controles que você conhece."
        />
        <Destination
          to="/activity"
          icon={Activity}
          title="Atividades"
          description="Consulte o registro do que aconteceu na sua SALY."
        />
      </div>
      {pending.length > 0 && (
        <section className="card routine-next">
          <h2>Para não perder de vista</h2>
          {pending.slice(0, 3).map((r) => (
            <Link key={r.id} to="/agenda">
              <span className="routine-leaf">
                <Leaf size={16} />
              </span>
              <span>
                {r.title}
                <small>
                  {r.due_at
                    ? new Date(r.due_at).toLocaleString("pt-BR")
                    : "Sem data definida"}
                </small>
              </span>
              <ArrowUpRight size={17} />
            </Link>
          ))}
        </section>
      )}
    </div>
  );
}
export function AdvancedHome() {
  return (
    <div className="area-home">
      <AreaIntro eyebrow="AJUSTES" title="Do seu jeito.">
        Preferências e recursos avançados, sempre ao seu alcance.
      </AreaIntro>
      <div className="destination-grid compact-destinations">
        <Destination
          to="/settings"
          icon={SlidersHorizontal}
          title="Preferências"
          description="Aparência, personalidade e notificações."
        />
        <Destination
          to="/settings/privacy"
          icon={ShieldCheck}
          title="Privacidade"
          description="Autorizações, uso de contexto e controle dos dados."
        />
        <Destination
          to="/voices"
          icon={Mic}
          title="Voz e escuta"
          description="Catálogo, prévias reais e voz selecionada."
        />
        <Destination
          to="/advanced/media"
          icon={Film}
          title="Provedores de mídia"
          description="Disponibilidade, configuração e limites da geração."
        />
        <Destination
          to="/settings/system"
          icon={HardDrive}
          title="Conexão e dispositivo"
          description="Modelo, armazenamento e funcionamento offline."
        />
        <Destination
          to="/tools"
          icon={Wrench}
          title="Ferramentas e integrações"
          description="Recursos internos, permissões e ações que exigem aprovação."
        />
        <Destination
          to="/laboratory"
          icon={FlaskConical}
          title="Laboratório SALY"
          description="Verificações reais e diagnósticos de compatibilidade."
        />
        <Destination
          to="/evaluation"
          icon={Activity}
          title="Avaliação"
          description="Consulte resultados, versões e evidências."
        />
        <Destination
          to="/offline"
          icon={ShieldCheck}
          title="Cofre local"
          description="Cópias escolhidas, cifradas neste dispositivo."
        />
      </div>
    </div>
  );
}
export function MediaAdvanced() {
  const [caps, setCaps] = useState<Data | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    api("/media/capabilities")
      .then(setCaps)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <div className="area-home">
      <AreaIntro eyebrow="MÍDIA · AVANÇADO" title="Motores e provedores.">
        Os arquivos e a criação ficam no Estúdio. Aqui estão a disponibilidade e
        os limites.
      </AreaIntro>
      <Link className="file-button" to="/studio">
        ← Voltar à Mídia
      </Link>
      {error && <p role="alert">{error}</p>}
      {caps ? (
        <div className="destination-grid">
          <section className="card">
            <h2>Geração de imagem</h2>
            <p>
              {caps.image_generation.provider} · {caps.image_generation.model}
            </p>
            <p>
              {caps.image_generation.configured
                ? "Configuração detectada; validação por geração real necessária."
                : "Não configurada."}
            </p>
            <p>{caps.image_generation.reason}</p>
            <p>
              O contrato existente usa Workers Free, sem ativação de cobrança. A
              franquia publicada é compartilhada pela conta; o limite adicional
              da SALY é uma requisição por dia UTC. Cada envio continua
              dependendo da sua confirmação.
            </p>
          </section>
          <section className="card">
            <h2>Geração de vídeo</h2>
            <p>{caps.video_generation.reason}</p>
            <p>
              Montagens de arquivos próprios são uma função separada da geração
              de novas cenas.
            </p>
          </section>
          <section className="card">
            <h2>Montagem e edição locais</h2>
            <p>
              {caps.montage.available
                ? "FFmpeg/FFprobe disponíveis."
                : "FFmpeg/FFprobe não encontrados no servidor."}
            </p>
            <p>
              Até oito cenas e sessenta segundos. Arquivos privados e exportação
              verificável; servidor ativo necessário.
            </p>
          </section>
          <section className="card">
            <h2>Credenciais e privacidade</h2>
            <p>
              Chaves permanecem no servidor. Esta interface não solicita, exibe
              nem copia segredos. Nenhum provedor pago foi habilitado pela
              reformulação.
            </p>
          </section>
        </div>
      ) : (
        !error && <p role="status">Consultando disponibilidade…</p>
      )}
    </div>
  );
}
