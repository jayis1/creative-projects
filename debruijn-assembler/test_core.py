from debruijn_assembler.core import assemble, build_graph, parse_reads


def test_build_graph_counts_kmers():
    graph, count = build_graph(["ACGTA"], 3)
    assert count == 3
    assert graph["AC"]["CG"] == 1


def test_assemble_reconstructs_linear_read():
    result = assemble(["ACGTAC"], k=3)
    assert "ACGTAC" in result.contigs


def test_parse_newline_reads():
    assert parse_reads("acg\nttt\n") == ["ACG", "TTT"]
