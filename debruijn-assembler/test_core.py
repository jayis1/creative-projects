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


def test_parse_fasta_multiline_and_fastq_validation():
    assert parse_reads(">a\nac\ngt\n>b\nttt\n") == ["ACGT", "TTT"]
    assert parse_reads("@r\nACGT\n+\n!!!!\n") == ["ACGT"]


def test_min_count_prunes_rare_kmers_and_reports_n50():
    result = assemble(["ACGT", "ACGT", "TTT"], k=3, min_count=2)
    assert result.contigs == ("ACGT",)
    assert result.n50 == 4
    assert result.graph_nodes == 3


def test_fasta_empty_record_is_rejected_but_can_be_lenient():
    import pytest
    with pytest.raises(ValueError, match="no sequence"):
        parse_reads(">empty\n>valid\nACGT\n")
    assert parse_reads(">empty\n>valid\nACGT\n", strict=False) == ["ACGT"]


def test_branching_graph_emits_each_contig_without_crashing():
    result = assemble(["AAT", "ATC", "ATG"], k=3)
    assert result.contigs == ("AAT", "ATC", "ATG")
