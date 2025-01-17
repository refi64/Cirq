"""Tests for the Quantum Volume benchmarker."""

from unittest.mock import Mock, MagicMock
import io
import numpy as np
from examples.advanced import quantum_volume
import cirq


def test_generate_model_circuit():
    """Test that a model circuit is randomly generated."""
    model_circuit = quantum_volume.generate_model_circuit(
        3, 3, random_state=np.random.RandomState(1))

    assert len(model_circuit) == 3
    # Ensure there are no measurement gates.
    assert list(
        model_circuit.findall_operations_with_gate_type(
            cirq.MeasurementGate)) == []


def test_generate_model_circuit_without_seed():
    """Test that a model circuit is randomly generated without a seed."""
    model_circuit = quantum_volume.generate_model_circuit(3, 3)

    assert len(model_circuit) == 3
    # Ensure there are no measurement gates.
    assert list(
        model_circuit.findall_operations_with_gate_type(
            cirq.MeasurementGate)) == []


def test_generate_model_circuit_seed():
    """Test that a model circuit is determined by its seed ."""
    model_circuit_1 = quantum_volume.generate_model_circuit(
        3, 3, random_state=np.random.RandomState(1))
    model_circuit_2 = quantum_volume.generate_model_circuit(
        3, 3, random_state=np.random.RandomState(1))
    model_circuit_3 = quantum_volume.generate_model_circuit(
        3, 3, random_state=np.random.RandomState(2))

    assert model_circuit_1 == model_circuit_2
    assert model_circuit_2 != model_circuit_3


def test_compute_heavy_set():
    """Test that the heavy set can be computed from a given circuit."""
    a, b, c = cirq.LineQubit.range(3)
    model_circuit = cirq.Circuit([
        cirq.Moment([]),
        cirq.Moment([cirq.X(a), cirq.Y(b)]),
        cirq.Moment([]),
        cirq.Moment([cirq.CNOT(a, c)]),
        cirq.Moment([cirq.Z(a), cirq.H(b)])
    ])
    assert quantum_volume.compute_heavy_set(model_circuit) == [5, 7]


def test_sample_heavy_set():
    """Test that we correctly sample a circuit's heavy set"""

    sampler = Mock(spec=cirq.Simulator)
    # Construct a result that returns "1", "2", "3", and then "0" indefinitely
    result = cirq.TrialResult.from_single_parameter_set(
        params=cirq.ParamResolver({}),
        measurements={'mock': np.array([[0, 1], [1, 0], [1, 1], [0, 0]])})
    sampler.run = MagicMock(return_value=result)
    circuit = cirq.Circuit(cirq.measure(*cirq.LineQubit.range(2)))

    probability = quantum_volume.sample_heavy_set(circuit, [1, 2, 3],
                                                  sampler=sampler,
                                                  repetitions=1000)
    # The first 3 of our outputs are in the heavy set, and then the rest are
    # not.
    assert probability == .003


def test_compile_circuit_router():
    """Tests that the given router is used."""
    router_mock = MagicMock()
    quantum_volume.compile_circuit(cirq.Circuit(),
                                   device=cirq.google.Bristlecone,
                                   router=router_mock)
    router_mock.assert_called()


def test_compile_circuit():
    """Tests that we are able to compile a model circuit."""
    compiler_mock = MagicMock(side_effect=lambda circuit: circuit)
    a, b, c = cirq.LineQubit.range(3)
    model_circuit = cirq.Circuit([
        cirq.Moment([cirq.X(a), cirq.Y(b), cirq.Z(c)]),
    ])
    [compiled_circuit,
     mapping] = quantum_volume.compile_circuit(model_circuit,
                                               device=cirq.google.Bristlecone,
                                               compiler=compiler_mock)

    assert len(mapping) == 3
    assert cirq.contrib.routing.ops_are_consistent_with_device_graph(
        compiled_circuit.all_operations(),
        cirq.contrib.routing.xmon_device_to_graph(cirq.google.Bristlecone))
    compiler_mock.assert_called_with(compiled_circuit)


def test_calculate_quantum_volume_result():
    """Test that running the main loop returns the desired result"""
    results = quantum_volume.calculate_quantum_volume(
        num_qubits=3,
        depth=3,
        num_repetitions=1,
        device=cirq.google.Bristlecone,
        samplers=[cirq.Simulator()],
        seed=1)

    model_circuit = quantum_volume.generate_model_circuit(
        3, 3, random_state=np.random.RandomState(1))
    assert len(results) == 1
    assert results[0].model_circuit == model_circuit
    assert results[0].heavy_set == quantum_volume.compute_heavy_set(
        model_circuit)
    assert len(results[0].sampler_result) == 1
    # Ensure that calling to_json on the results does not err.
    buffer = io.StringIO()
    cirq.to_json(results, buffer)


def test_main_loop():
    """Test that the main loop is able to run without erring."""
    # Keep test from taking a long time by lowering repetitions.
    args = '--num_qubits 5 --depth 5 --num_repetitions 1'.split()
    quantum_volume.main(**quantum_volume.parse_arguments(args))


def test_calculate_quantum_volume_loop():
    """Test that calculate_quantum_volume is able to run without erring."""
    # Keep test from taking a long time by lowering repetitions.
    quantum_volume.calculate_quantum_volume(num_qubits=5,
                                            depth=5,
                                            num_repetitions=1,
                                            seed=1,
                                            device=cirq.google.Bristlecone,
                                            samplers=[cirq.Simulator()])


def test_parse_args():
    """Test that an argument string is parsed correctly."""
    args = (
        '--num_qubits 5 --depth 5 --num_repetitions 200 --seed 1234').split()
    kwargs = quantum_volume.parse_arguments(args)
    assert kwargs == {
        'num_qubits': 5,
        'depth': 5,
        'num_repetitions': 200,
        'seed': 1234,
    }
