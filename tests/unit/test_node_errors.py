import pytest
from griptape_nodes.exe_types.core_types import NodeError

from griptape_nodes_library_seedvr.seedvr2_image_upscale import SeedVR2ImageUpscale
from griptape_nodes_library_seedvr.seedvr2_video_upscale import SeedVR2VideoUpscale

CASES = [
    (SeedVR2ImageUpscale, "input_image", "Connect an image to 'Input Image'."),
    (SeedVR2VideoUpscale, "input_video", "Connect a video to 'Input Video'."),
]


def _bare(cls, **values):
    node = object.__new__(cls)
    node.parameter_values = dict(values)
    return node


@pytest.mark.parametrize(("cls", "param", "message"), CASES)
def test_missing_input_and_model_are_node_errors(monkeypatch, cls, param, message):
    monkeypatch.setattr(cls, "_is_model_downloaded", lambda _self, _repo: False)
    errors = _bare(cls).validate_before_node_run()
    assert errors is not None
    assert all(isinstance(error, NodeError) for error in errors)
    assert str(errors[0]) == message
    assert errors[0].fields == {"parameter": param}
    model_error = errors[1]
    assert str(model_error) == (
        "The model 'ByteDance-Seed/SeedVR2-3B' is not downloaded. "
        "Download it in the Model Manager, then run the node again."
    )
    assert [link.url for link in model_error.links] == ["#model-management"]


@pytest.mark.parametrize(("cls", "param", "message"), CASES)
def test_valid_inputs_pass_validation(monkeypatch, cls, param, message):
    monkeypatch.setattr(cls, "_is_model_downloaded", lambda _self, _repo: True)
    assert _bare(cls, **{param: object()}).validate_before_node_run() is None


@pytest.mark.parametrize(("cls", "param", "message"), CASES)
def test_cuda_only_error(monkeypatch, cls, param, message):
    monkeypatch.setattr(cls, "execution_device", property(lambda _self: "mps"))
    errors = _bare(cls).validate_in_execution_environment()
    assert errors is not None
    assert isinstance(errors[0], NodeError)
    assert str(errors[0]).startswith("SeedVR2 runs on CUDA only, and the engine reports 'mps'")
    assert errors[0].fields == {"device": "mps"}
