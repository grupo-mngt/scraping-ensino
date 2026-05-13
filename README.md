# scraping-ensino

## Panorama dos cursos

O diretório `downloads/` reúne **21 cursos** da trilha Senior, divididos em três grandes blocos: **WMS Senior** (gestão de armazenagem), **Senior AI Logistics** e **Suporte Responde HCM**. O arquivo `downloads/_indice.json` lista todos os cursos com o respectivo percentual de andamento na plataforma.

### Como cada curso está organizado

Cada pasta de curso segue o mesmo padrão:

```
<Nome do Curso>/
  <Módulo ou Tópico 1>/
    01 - <Aula>.mp4
  <Módulo ou Tópico 2>/
    01 - <Aula>.mp4
  Apostila <...>.pdf
  Documentação.htm        # quando existe
```

- **Subpastas** representam os módulos/temas do curso (ex.: *Cadastro de Usuários*, *Dashboards*, *Notificações*).
- **Vídeos `.mp4`** são as aulas, numeradas em sequência (`01 - ...`, `02 - ...`).
- **Apostila em PDF** fica na raiz da pasta do curso e cobre o conteúdo completo do mesmo.
- Alguns cursos também trazem uma **`Documentação.htm`** com material complementar.

### Blocos de conteúdo

**WMS Senior — Fundamentos e Implantação**
- Introdução Gestão de Armazenagem WMS Senior
- Implantação do WMS X
- Operação do WMS X
- Parametrizações Iniciais
- Módulo Enterprise
- Módulo Mobile

**WMS Senior — Processos Operacionais**
- Processo de Recebimento
- Recebimento por Amostragem
- Processo de Separação e Expedição
- Processo de Movimentação
- Processo de Inventário
- Processo de Devolução de Mercadorias
- Conferência Alocada
- Processos Armazém Geral
- Fluxo Industrialização/Manufatura

**WMS Senior — Ferramentas**
- Gerenciador de Etiquetas
- Integração REST

**Senior AI Logistics**
- Curso único cobrindo Apresentação, Dashboards, Navegação, Notificações, Repositórios, Usuários e Encerramento.

**Suporte Responde HCM**
- Documentação técnica e abertura de chamados
- Dissídio Coletivo
- Médias no Administração de Pessoal

### Tamanhos típicos

- Vídeos variam de ~25 MB (aulas curtas, ex.: *Conferência Alocada*) a ~250 MB (aulas longas, ex.: *Dissídio Coletivo*).
- Apostilas ficam entre ~1 MB e ~4 MB, dependendo da extensão do curso.
