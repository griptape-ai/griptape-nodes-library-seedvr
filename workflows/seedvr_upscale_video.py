# /// script
# dependencies = []
#
# [tool.griptape-nodes]
# name = "seedvr_upscale_video"
# schema_version = "0.20.0"
# engine_version_created_with = "0.99.0"
# node_libraries_referenced = [["Griptape Nodes SeedVR Library", "0.1.0"], ["Griptape Nodes Library", "0.84.0"]]
# node_types_used = [["Griptape Nodes Library", "CompareVideos"], ["Griptape Nodes Library", "LoadVideo"], ["Griptape Nodes SeedVR Library", "SeedVR2VideoUpscale"]]
# description = "Demonstrates the use of SeedVR2 Video Upscaling"
# image = "https://raw.githubusercontent.com/griptape-ai/griptape-nodes-library-seedvr/refs/heads/main/workflows/templates/seedvr_upscale_video.webp"
# is_griptape_provided = true
# is_template = true
# is_internal = false
# creation_date = 2026-08-18T22:10:46.409308Z
# last_modified_date = 2026-08-30T18:16:27.871906Z
#
# ///

import pickle

from griptape.artifacts.video_url_artifact import VideoUrlArtifact
from griptape_nodes.node_library.library_registry import IconVariant, NodeDeprecationMetadata, NodeMetadata
from griptape_nodes.retained_mode.events.connection_events import CreateConnectionRequest
from griptape_nodes.retained_mode.events.flow_events import CreateFlowRequest
from griptape_nodes.retained_mode.events.library_events import RegisterLibraryFromFileRequest
from griptape_nodes.retained_mode.events.node_events import CreateNodeRequest
from griptape_nodes.retained_mode.events.parameter_events import (
    AddParameterToNodeRequest,
    AlterParameterDetailsRequest,
    SetParameterValueRequest,
)
from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes


async def build_workflow() -> None:
    await GriptapeNodes.ahandle_request(
        RegisterLibraryFromFileRequest(
            library_name="Griptape Nodes SeedVR Library", perform_discovery_if_not_found=True
        )
    )
    await GriptapeNodes.ahandle_request(
        RegisterLibraryFromFileRequest(library_name="Griptape Nodes Library", perform_discovery_if_not_found=True)
    )
    context_manager = GriptapeNodes.ContextManager()
    if not context_manager.has_current_workflow():
        context_manager.push_workflow(file_path=__file__)
    # 1. We've collated all of the unique parameter values into a dictionary so that we do not have to duplicate them.
    #    This minimizes the size of the code, especially for large objects like serialized image files.
    # 2. We're using a prefix so that it's clear which Flow these values are associated with.
    # 3. The values are serialized using pickle, which is a binary format. This makes them harder to read, but makes
    #    them consistently save and load. It allows us to serialize complex objects like custom classes, which otherwise
    #    would be difficult to serialize.
    top_level_unique_values_dict = {
        "7547ea79-8e39-468f-8e38-d5b31c24b06c": pickle.loads(
            b"\x80\x04\x95\x84\x01\x00\x00\x00\x00\x00\x00\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94\x8c\x10VideoUrlArtifact\x94\x8c\x0bmodule_name\x94\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x02id\x94\x8c db47fc55cd0f4cda854880c6b6c4cf37\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94h\n\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94ub."
        ),
        "87cc9bd3-705f-4ee9-bf1a-378cae5dc112": pickle.loads(
            b"\x80\x04\x95M\x01\x00\x00\x00\x00\x00\x00\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94h\x01\x8c\x0bmodule_name\x94h\x00\x8c\x02id\x94\x8c e8fd21a19b7b4a70986432d44b1d029b\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94h\x08\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94ub."
        ),
        "e2c57a22-f10d-4f44-98f3-956a7daed4f9": pickle.loads(
            b"\x80\x04\x95k\x00\x00\x00\x00\x00\x00\x00\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94."
        ),
        "fc6261e1-f4e2-46bc-982e-4ccc7bdfae61": pickle.loads(
            b"\x80\x04\x95\x8d\x00\x00\x00\x00\x00\x00\x00\x8c\x89C:\\Users\\JasonSchleifer\\Documents\\GriptapeNodes/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94."
        ),
        "f28c34f3-ab29-4e71-80c6-178d76ba60e5": pickle.loads(
            b"\x80\x04\x95?\x01\x00\x00\x00\x00\x00\x00\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94\x8c\x10VideoUrlArtifact\x94\x8c\x0bmodule_name\x94h\x00\x8c\x02id\x94\x8c 1e0ea414a8a44e118eb2b12509f77f84\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94\x8c 1e0ea414a8a44e118eb2b12509f77f84\x94\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8c'{outputs}/videos/seedvr2_video_v012.mp4\x94ub."
        ),
        "00873c58-5c73-4717-bbd3-2e4f3f03c569": pickle.loads(
            b"\x80\x04\x95\x19\x02\x00\x00\x00\x00\x00\x00}\x94(\x8c\rinput_video_1\x94\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94h\x03\x8c\x0bmodule_name\x94h\x02\x8c\x02id\x94\x8c e8fd21a19b7b4a70986432d44b1d029b\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94h\n\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94ub\x8c\rinput_video_2\x94h\x04)\x81\x94}\x94(h\x07\x8c\x10VideoUrlArtifact\x94h\x08h\x02h\t\x8c 1e0ea414a8a44e118eb2b12509f77f84\x94h\x0bNh\x0c}\x94h\x0e\x8c 1e0ea414a8a44e118eb2b12509f77f84\x94h\x0fh\x10h\x11h\x12h\x13\x8c'{outputs}/videos/seedvr2_video_v012.mp4\x94ubu."
        ),
        "9e279902-89f6-40a8-b293-b734080a3815": pickle.loads(
            b"\x80\x04\x95\x19\x02\x00\x00\x00\x00\x00\x00}\x94(\x8c\rinput_video_1\x94\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94h\x03\x8c\x0bmodule_name\x94h\x02\x8c\x02id\x94\x8c e8fd21a19b7b4a70986432d44b1d029b\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94h\n\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94ub\x8c\rinput_video_2\x94h\x04)\x81\x94}\x94(h\x07\x8c\x10VideoUrlArtifact\x94h\x08h\x02h\t\x8c 1e0ea414a8a44e118eb2b12509f77f84\x94h\x0bNh\x0c}\x94h\x0e\x8c 1e0ea414a8a44e118eb2b12509f77f84\x94h\x0fh\x10h\x11h\x12h\x13\x8c'{outputs}/videos/seedvr2_video_v012.mp4\x94ubu."
        ),
        "7c6466d5-0cd0-4dfe-bd19-2bbe7f8fb4b2": pickle.loads(
            b"\x80\x04\x95\x1d\x00\x00\x00\x00\x00\x00\x00\x8c\x19ByteDance-Seed/SeedVR2-3B\x94."
        ),
        "f7f86494-05c4-44c7-bd88-79b1bf50bbc2": pickle.loads(
            b"\x80\x04\x95M\x01\x00\x00\x00\x00\x00\x00\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94h\x01\x8c\x0bmodule_name\x94h\x00\x8c\x02id\x94\x8c fad249a174f24e358e90c63fe490636e\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94h\x08\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94ub."
        ),
        "0349f780-9f61-42cb-bb47-a70882ad430e": pickle.loads(
            b"\x80\x04\x95\t\x00\x00\x00\x00\x00\x00\x00\x8c\x05scale\x94."
        ),
        "77120921-524a-4f94-b19e-7d8048ea73d9": pickle.loads(
            b"\x80\x04\x95\x06\x00\x00\x00\x00\x00\x00\x00\x8c\x022x\x94."
        ),
        "43fce989-4cac-46c8-8879-67fcf1ffeb44": pickle.loads(b"\x80\x04\x95\x04\x00\x00\x00\x00\x00\x00\x00M\x00\x05."),
        "246d1323-3897-467f-aecc-0b6ad4b7a38e": pickle.loads(b"\x80\x04\x95\x04\x00\x00\x00\x00\x00\x00\x00M\xd0\x02."),
        "5f5361b3-dae5-4073-b5f0-905839466d54": pickle.loads(b"\x80\x04K)."),
        "38ca973f-629d-4db8-8b11-065fd145f434": pickle.loads(b"\x80\x04K\x02."),
        "60c4fb85-a093-4987-8755-4f070a8f5350": pickle.loads(b"\x80\x04\x89."),
        "1c9ef8df-39e2-4199-aaa9-ef2da56456df": pickle.loads(b"\x80\x04K*."),
        "94f83786-2248-4611-9bce-d9e044d94876": pickle.loads(
            b"\x80\x04\x95\xb9\x00\x00\x00\x00\x00\x00\x00}\x94(\x8c\x04type\x94\x8c\x10VideoUrlArtifact\x94\x8c\x02id\x94\x8c 1e0ea414a8a44e118eb2b12509f77f84\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94\x8c 1e0ea414a8a44e118eb2b12509f77f84\x94\x8c\x05value\x94\x8c'{outputs}/videos/seedvr2_video_v012.mp4\x94u."
        ),
        "691935eb-0534-4c0b-a68f-2cf5a954a7b2": pickle.loads(
            b"\x80\x04\x95\x15\x00\x00\x00\x00\x00\x00\x00\x8c\x11seedvr2_video.mp4\x94."
        ),
        "26191b2c-ef78-45f0-9c41-497800be3447": pickle.loads(b"\x80\x04\x88."),
        "409cff80-84ce-4d49-a3b7-667e9b4ec6dd": pickle.loads(
            b"\x80\x04\x95(\x00\x00\x00\x00\x00\x00\x00\x8c$SUCCESS: Video upscaled successfully\x94."
        ),
    }
    # Create the Flow, then do work within it as context.
    flow0_name = (
        await GriptapeNodes.ahandle_request(
            CreateFlowRequest(parent_flow_name=None, flow_name="ControlFlow_1", set_as_new_context=False, metadata={})
        )
    ).flow_name
    with GriptapeNodes.ContextManager().flow(flow0_name):
        node0_name = (
            await GriptapeNodes.ahandle_request(
                CreateNodeRequest(
                    node_type="LoadVideo",
                    specific_library_name="Griptape Nodes Library",
                    node_name="Load Video",
                    metadata={
                        "position": {"x": 637.5547872976261, "y": 521.2456333217535},
                        "tempId": "placing-1787092157793-hsv66f",
                        "library_node_metadata": {
                            "category": "video",
                            "description": "Loads video files into your workflow",
                            "display_name": "Load Video",
                            "tags": ["video", "file", "load"],
                            "icon": "file-video",
                            "color": None,
                            "group": "Input/Output",
                            "deprecation": None,
                            "is_node_group": None,
                            "declarations": [],
                        },
                        "library": "Griptape Nodes Library",
                        "node_type": "LoadVideo",
                        "showaddparameter": False,
                        "size": {"width": 824, "height": 705},
                    },
                    resolution="resolved",
                    initial_setup=True,
                )
            )
        ).node_name
        node1_name = (
            await GriptapeNodes.ahandle_request(
                CreateNodeRequest(
                    node_type="CompareVideos",
                    specific_library_name="Griptape Nodes Library",
                    node_name="Compare Videos",
                    metadata={
                        "position": {"x": 2443.609620022385, "y": 521.2456333217535},
                        "tempId": "placing-1787092305824-bnqxk7",
                        "library_node_metadata": {
                            "category": "video",
                            "description": "Can be used to compare two videos",
                            "display_name": "Compare Videos",
                            "tags": ["video", "compare"],
                            "icon": "square-split-horizontal",
                            "color": None,
                            "group": "display",
                            "deprecation": None,
                            "is_node_group": None,
                            "declarations": [],
                            "resolved_model_usage": [],
                        },
                        "library": "Griptape Nodes Library",
                        "node_type": "CompareVideos",
                        "showaddparameter": False,
                        "size": {"width": 1029, "height": 843},
                    },
                    resolution="resolved",
                    initial_setup=True,
                )
            )
        ).node_name
        node2_name = (
            await GriptapeNodes.ahandle_request(
                CreateNodeRequest(
                    node_type="SeedVR2VideoUpscale",
                    specific_library_name="Griptape Nodes SeedVR Library",
                    node_name="SeedVR2 Video Upscale",
                    metadata={
                        "library_node_metadata": {
                            "category": "video",
                            "description": "Upscales and restores a video using SeedVR2, a one-step diffusion transformer model from ByteDance. Handles model download, caching, and GPU inference automatically.",
                            "display_name": "SeedVR2 Video Upscale",
                            "tags": None,
                            "icon": None,
                            "color": None,
                            "group": "edit",
                            "deprecation": None,
                            "is_node_group": None,
                            "declarations": [],
                        },
                        "library": "Griptape Nodes SeedVR Library",
                        "node_type": "SeedVR2VideoUpscale",
                        "position": {"x": 1615.3429509475916, "y": 722.3547577246228},
                        "size": {"width": 600, "height": 1112},
                    },
                    resolution="resolved",
                    initial_setup=True,
                )
            )
        ).node_name
        await GriptapeNodes.ahandle_request(
            CreateConnectionRequest(
                source_node_name=node0_name,
                source_parameter_name="video",
                target_node_name=node1_name,
                target_parameter_name="Video_1",
                initial_setup=True,
            )
        )
        await GriptapeNodes.ahandle_request(
            CreateConnectionRequest(
                source_node_name=node0_name,
                source_parameter_name="video",
                target_node_name=node2_name,
                target_parameter_name="input_video",
                initial_setup=True,
            )
        )
        await GriptapeNodes.ahandle_request(
            CreateConnectionRequest(
                source_node_name=node2_name,
                source_parameter_name="output_video",
                target_node_name=node1_name,
                target_parameter_name="Video_2",
                initial_setup=True,
            )
        )
        with GriptapeNodes.ContextManager().node(node0_name):
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="video",
                    node_name=node0_name,
                    value=top_level_unique_values_dict["7547ea79-8e39-468f-8e38-d5b31c24b06c"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="video",
                    node_name=node0_name,
                    value=top_level_unique_values_dict["87cc9bd3-705f-4ee9-bf1a-378cae5dc112"],
                    initial_setup=True,
                    is_output=True,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="path",
                    node_name=node0_name,
                    value=top_level_unique_values_dict["e2c57a22-f10d-4f44-98f3-956a7daed4f9"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="path",
                    node_name=node0_name,
                    value=top_level_unique_values_dict["fc6261e1-f4e2-46bc-982e-4ccc7bdfae61"],
                    initial_setup=True,
                    is_output=True,
                )
            )
        with GriptapeNodes.ContextManager().node(node1_name):
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="Video_1",
                    node_name=node1_name,
                    value=top_level_unique_values_dict["87cc9bd3-705f-4ee9-bf1a-378cae5dc112"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="Video_2",
                    node_name=node1_name,
                    value=top_level_unique_values_dict["f28c34f3-ab29-4e71-80c6-178d76ba60e5"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="Compare",
                    node_name=node1_name,
                    value=top_level_unique_values_dict["00873c58-5c73-4717-bbd3-2e4f3f03c569"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="Compare",
                    node_name=node1_name,
                    value=top_level_unique_values_dict["9e279902-89f6-40a8-b293-b734080a3815"],
                    initial_setup=True,
                    is_output=True,
                )
            )
        with GriptapeNodes.ContextManager().node(node2_name):
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="model",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["7c6466d5-0cd0-4dfe-bd19-2bbe7f8fb4b2"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="input_video",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["f7f86494-05c4-44c7-bd88-79b1bf50bbc2"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="resize_mode",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["0349f780-9f61-42cb-bb47-a70882ad430e"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="scale",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["77120921-524a-4f94-b19e-7d8048ea73d9"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="output_width",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["43fce989-4cac-46c8-8879-67fcf1ffeb44"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="output_height",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["246d1323-3897-467f-aecc-0b6ad4b7a38e"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="batch_size",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["5f5361b3-dae5-4073-b5f0-905839466d54"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="temporal_overlap",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["38ca973f-629d-4db8-8b11-065fd145f434"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="randomize_seed",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["60c4fb85-a093-4987-8755-4f070a8f5350"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="seed",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["1c9ef8df-39e2-4199-aaa9-ef2da56456df"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="output_video",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["94f83786-2248-4611-9bce-d9e044d94876"],
                    initial_setup=True,
                    is_output=True,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="output_file",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["691935eb-0534-4c0b-a68f-2cf5a954a7b2"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="was_successful",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["60c4fb85-a093-4987-8755-4f070a8f5350"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="was_successful",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["26191b2c-ef78-45f0-9c41-497800be3447"],
                    initial_setup=True,
                    is_output=True,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="result_details",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["409cff80-84ce-4d49-a3b7-667e9b4ec6dd"],
                    initial_setup=True,
                    is_output=True,
                )
            )
