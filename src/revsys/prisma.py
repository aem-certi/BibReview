"""
Módulo para geração de relatório PRISMA simplificado.
"""

__all__ = ['generate_prisma_report', 'generate_prisma_diagram']

def generate_prisma_report(counts: dict) -> str:
    """
    Gera um sumário textual simples do fluxo PRISMA.

    Args:
        counts: dicionário com chaves: 'identified', 'pretriage', 'triaged', 'fulltext'
    Returns:
        Texto formatado do relatório PRISMA.
    """
    lines = []
    iden = counts.get('identified')
    if iden is not None:
        lines.append(f"Records identified: {iden}")
    pre = counts.get('pretriage')
    if pre is not None:
        lines.append(f"After pre-triage: {pre}")
    tri = counts.get('triaged')
    if tri is not None:
        lines.append(f"After triage: {tri}")
    ful = counts.get('fulltext')
    if ful is not None:
        lines.append(f"Full-text retrieved: {ful}")
    return "\n".join(lines)
import os

def generate_prisma_diagram(counts: dict, output_file: str = 'prisma_flowchart.png') -> str:
    """
    Gera um fluxograma PRISMA como diagrama visual.

    Args:
        counts: dicionário com chaves: 'identified', 'pretriage', 'triaged', 'fulltext'
        output_file: caminho para salvar o diagrama (incluindo extensão, ex: .png ou .svg)
    Returns:
        Caminho do arquivo gerado.
    """
    try:
        from graphviz import Digraph
    except ImportError:
        raise RuntimeError('graphviz library is required to generate PRISMA diagram')
    # Determina formato a partir da extensão e inicia o Digraph
    name, ext = os.path.splitext(output_file)
    fmt = ext.lstrip('.').lower() or 'png'
    dot = Digraph('PRISMA', format=fmt)
    # Mapeamento de estágios: (node_id, counts_key, display_name)
    stages = [
        ('A', 'identified', 'Identified'),
        ('B', 'pretriage', 'After pre-triage'),
        ('C', 'triaged', 'After triage'),
        ('D', 'fulltext', 'Full-text retrieved'),
    ]
    # Nomes para exclusões em cada estágio
    excl_labels = {
        'pretriage': 'Excluded after pre-triage',
        'triaged': 'Excluded after triage',
        'fulltext': 'Full-text not retrieved',
    }
    # Lista dos nós efetivamente adicionados (node_id, key)
    added = []
    for idx, (node_id, key, disp_name) in enumerate(stages):
        count = counts.get(key)
        if count is None:
            continue
        # Adiciona nó principal
        dot.node(node_id, f"{disp_name}\n{count}")
        # Se há estágio anterior válido, conecta e calcula excluídos
        if added:
            prev_id, prev_key = added[-1]
            prev_count = counts.get(prev_key, 0) or 0
            curr_count = count or 0
            # Cria nó de excluídos se houver remanejamento
            excl = prev_count - curr_count
            if excl > 0 and key in excl_labels:
                e_id = f"E{idx}"
                label = f"{excl_labels[key]}\n{excl}"
                dot.node(e_id, label)
                dot.edge(prev_id, e_id)
            # Conecta inclusão ao próximo estágio
            dot.edge(prev_id, node_id)
        # Registra este nó como adicionado
        added.append((node_id, key))
    # Renderiza e retorna o caminho
    output_path = dot.render(filename=name, cleanup=True)
    return output_path