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

from griptape_nodes.retained_mode.events.connection_events import CreateConnectionRequest
from griptape_nodes.retained_mode.events.flow_events import CreateFlowRequest
from griptape_nodes.retained_mode.events.library_events import RegisterLibraryFromFileRequest
from griptape_nodes.retained_mode.events.node_events import CreateNodeRequest
from griptape_nodes.retained_mode.events.parameter_events import SetParameterValueRequest
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
        "23d9ad9e-8e35-469e-b77a-be87787ab39b": pickle.loads(
            b"\x80\x04\x95\x84\x01\x00\x00\x00\x00\x00\x00\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94\x8c\x10VideoUrlArtifact\x94\x8c\x0bmodule_name\x94\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x02id\x94\x8c db47fc55cd0f4cda854880c6b6c4cf37\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94h\n\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94ub."
        ),
        "706ac32e-5700-4713-b135-d32ad42364a3": pickle.loads(
            b"\x80\x04\x95\x84\x01\x00\x00\x00\x00\x00\x00\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94\x8c\x10VideoUrlArtifact\x94\x8c\x0bmodule_name\x94\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x02id\x94\x8c e8fd21a19b7b4a70986432d44b1d029b\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94h\n\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94ub."
        ),
        "cbd2a469-638e-431d-9047-a0048cb27b04": pickle.loads(
            b"\x80\x04\x95k\x00\x00\x00\x00\x00\x00\x00\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94."
        ),
        "2742af62-a8b3-4862-acbe-92af97171aae": pickle.loads(
            b"\x80\x04\x95\x8d\x00\x00\x00\x00\x00\x00\x00\x8c\x89C:\\Users\\JasonSchleifer\\Documents\\GriptapeNodes/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94."
        ),
        "c8e1a097-6143-4a91-84ce-155a9ab74c12": pickle.loads(
            b"\x80\x04\x95\xa9\x01\x00\x00\x00\x00\x00\x00}\x94(\x8c\rinput_video_1\x94\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x10VideoUrlArtifact\x94\x93\x94)\x81\x94}\x94(\x8c\x04type\x94\x8c\x10VideoUrlArtifact\x94\x8c\x0bmodule_name\x94\x8c%griptape.artifacts.video_url_artifact\x94\x8c\x02id\x94\x8c e8fd21a19b7b4a70986432d44b1d029b\x94\x8c\treference\x94N\x8c\x04meta\x94}\x94\x8c\x04name\x94h\x0c\x8c\x16encoding_error_handler\x94\x8c\x06strict\x94\x8c\x08encoding\x94\x8c\x05utf-8\x94\x8c\x05value\x94\x8cg{project_dir}/libraries/griptape-nodes-library-seedvr/workflows/assets/videos/woman_sipping_low_res.mp4\x94ub\x8c\rinput_video_2\x94Nu."
        ),
        "0bc641e3-ce26-463b-a155-e6fb4e32592b": pickle.loads(
            b"\x80\x04\x95\x1d\x00\x00\x00\x00\x00\x00\x00\x8c\x19ByteDance-Seed/SeedVR2-3B\x94."
        ),
        "41ac16af-9eb4-49dc-afda-f7aebf0e94ca": pickle.loads(
            b"\x80\x04\x95\t\x00\x00\x00\x00\x00\x00\x00\x8c\x05scale\x94."
        ),
        "7ad16ea9-6289-4e30-ab52-df9d4facdb8f": pickle.loads(
            b"\x80\x04\x95\x06\x00\x00\x00\x00\x00\x00\x00\x8c\x022x\x94."
        ),
        "8b98969d-2345-4279-8bde-5be5c4003dbe": pickle.loads(b"\x80\x04\x95\x04\x00\x00\x00\x00\x00\x00\x00M\x00\x05."),
        "5be7b5fd-ce07-4713-ab27-28b87be7ca8c": pickle.loads(b"\x80\x04\x95\x04\x00\x00\x00\x00\x00\x00\x00M\xd0\x02."),
        "cae89f0d-c160-4fec-b5f4-b05e97a2bff3": pickle.loads(b"\x80\x04K)."),
        "565255dc-6ba6-4cfb-97af-78453a7023d4": pickle.loads(b"\x80\x04K\x02."),
        "5e23daa1-16ae-4ed2-b799-e090b7318cad": pickle.loads(b"\x80\x04\x89."),
        "a765e3af-28dc-4399-a0e4-6964984b9714": pickle.loads(b"\x80\x04K*."),
        "e97f9192-9884-418b-a4af-d18f241838a9": pickle.loads(
            b"\x80\x04\x95\x15\x00\x00\x00\x00\x00\x00\x00\x8c\x11seedvr2_video.mp4\x94."
        ),
        "8fc12bba-3907-4f26-b521-68b8b5886c67": pickle.loads(
            b"\x80\x04\x95\xf6\x00\x00\x00\x00\x00\x00\x00\x8c\xf2# Temporal Overlap\n\nHow many frames are shared between consecutive passes and blended together. \n\nA small overlap (2\xe2\x80\x934) smooths out any visible seams at pass boundaries. \n\nSet to 0 to disable blending entirely. Must be less than Batch Size.\x94."
        ),
        "d923924c-2771-46e9-b26f-40fe9f487df2": pickle.loads(
            b"\x80\x04\x95\x15\x01\x00\x00\x00\x00\x00\x00X\x0e\x01\x00\x00# Batch Size\n\nHow many frames are upscaled together in each pass. \nLarger values are faster (fewer passes) but use more GPU memory. \n\nIf you get an out-of-memory error, try cutting this in half. \n\nMust be 1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, ... (any `4n+1` number).\x94."
        ),
        "0d17da4a-3e2a-4ed3-96de-973244afec63": pickle.loads(
            b"\x80\x04\x95\xe7\x01\x00\x00\x00\x00\x00\x00X\xe0\x01\x00\x00# Upscale Video with SeedVR2\n\nThis node allows you to upscale a video using the SeedVR2 model.\n\nIn order to use it, you'll need to use the Model Manager to download either the 3B or 7B model. _Note: This will only work on a CUDA capable machine._\n\nClick on one of the following links to open the Model Manager and download the appropriate model\n\n* [SeedVR2-3B](#model-management?search=ByteDance-Seed/SeedVR2-3B)\n* [SeedVR2-7B](#model-management?search=ByteDance-Seed/SeedVR2-7B)\n\x94."
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
                        "position": {"x": 319.06289098609057, "y": 119.50401217887052},
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
                            "resolved_model_usage": [],
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
                        "position": {"x": 3516.2850228674497, "y": 119.50401217887052},
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
                            "resolved_model_usage": [],
                        },
                        "library": "Griptape Nodes SeedVR Library",
                        "node_type": "SeedVR2VideoUpscale",
                        "position": {"x": 1626.0771755652536, "y": 757.2409877320246},
                        "size": {"width": 882, "height": 1502},
                        "showaddparameter": False,
                    },
                    initial_setup=True,
                )
            )
        ).node_name
        node3_name = (
            await GriptapeNodes.ahandle_request(
                CreateNodeRequest(
                    node_type="Note",
                    specific_library_name="Griptape Nodes Library",
                    node_name="Temporal Overlap Note",
                    metadata={
                        "position": {"x": 2522.4805834381564, "y": 1151.9048164101616},
                        "tempId": "placing-1788195143929-5c6bn8",
                        "library_node_metadata": {
                            "category": "misc",
                            "description": "Create a note node to provide helpful context in your workflow",
                            "display_name": "Note",
                            "tags": ["workflow", "annotation", "note"],
                            "icon": "notepad-text",
                            "color": None,
                            "group": "create",
                            "deprecation": None,
                            "is_node_group": None,
                            "declarations": [],
                            "resolved_model_usage": [],
                        },
                        "library": "Griptape Nodes Library",
                        "node_type": "Note",
                        "showaddparameter": False,
                        "size": {"width": 606, "height": 318},
                        "color": "#0e7490",
                    },
                    initial_setup=True,
                )
            )
        ).node_name
        node4_name = (
            await GriptapeNodes.ahandle_request(
                CreateNodeRequest(
                    node_type="Note",
                    specific_library_name="Griptape Nodes Library",
                    node_name="Batch Size Note",
                    metadata={
                        "position": {"x": 990.9794829887672, "y": 1098.138259944119},
                        "tempId": "placing-1788195143929-5c6bn8",
                        "library_node_metadata": {
                            "category": "misc",
                            "description": "Create a note node to provide helpful context in your workflow",
                            "display_name": "Note",
                            "tags": ["workflow", "annotation", "note"],
                            "icon": "notepad-text",
                            "color": None,
                            "group": "create",
                            "deprecation": None,
                            "is_node_group": None,
                            "declarations": [],
                            "resolved_model_usage": [],
                        },
                        "library": "Griptape Nodes Library",
                        "node_type": "Note",
                        "showaddparameter": False,
                        "size": {"width": 606, "height": 318},
                        "color": "#0e7490",
                    },
                    initial_setup=True,
                )
            )
        ).node_name
        node5_name = (
            await GriptapeNodes.ahandle_request(
                CreateNodeRequest(
                    node_type="Note",
                    specific_library_name="Griptape Nodes Library",
                    node_name="SeedVR Node",
                    metadata={
                        "position": {"x": 1626.0771755652536, "y": 390.37269589130415},
                        "tempId": "placing-1788195143929-5c6bn8",
                        "library_node_metadata": {
                            "category": "misc",
                            "description": "Create a note node to provide helpful context in your workflow",
                            "display_name": "Note",
                            "tags": ["workflow", "annotation", "note"],
                            "icon": "notepad-text",
                            "color": None,
                            "group": "create",
                            "deprecation": None,
                            "is_node_group": None,
                            "declarations": [],
                            "resolved_model_usage": [],
                        },
                        "library": "Griptape Nodes Library",
                        "node_type": "Note",
                        "showaddparameter": False,
                        "size": {"width": 872, "height": 350},
                        "color": "#0e7490",
                    },
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
                    value=top_level_unique_values_dict["23d9ad9e-8e35-469e-b77a-be87787ab39b"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="video",
                    node_name=node0_name,
                    value=top_level_unique_values_dict["706ac32e-5700-4713-b135-d32ad42364a3"],
                    initial_setup=True,
                    is_output=True,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="path",
                    node_name=node0_name,
                    value=top_level_unique_values_dict["cbd2a469-638e-431d-9047-a0048cb27b04"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="path",
                    node_name=node0_name,
                    value=top_level_unique_values_dict["2742af62-a8b3-4862-acbe-92af97171aae"],
                    initial_setup=True,
                    is_output=True,
                )
            )
        with GriptapeNodes.ContextManager().node(node1_name):
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="Video_1",
                    node_name=node1_name,
                    value=top_level_unique_values_dict["706ac32e-5700-4713-b135-d32ad42364a3"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="Compare",
                    node_name=node1_name,
                    value=top_level_unique_values_dict["c8e1a097-6143-4a91-84ce-155a9ab74c12"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="Compare",
                    node_name=node1_name,
                    value=top_level_unique_values_dict["c8e1a097-6143-4a91-84ce-155a9ab74c12"],
                    initial_setup=True,
                    is_output=True,
                )
            )
        with GriptapeNodes.ContextManager().node(node2_name):
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="model",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["0bc641e3-ce26-463b-a155-e6fb4e32592b"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="input_video",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["706ac32e-5700-4713-b135-d32ad42364a3"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="resize_mode",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["41ac16af-9eb4-49dc-afda-f7aebf0e94ca"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="scale",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["7ad16ea9-6289-4e30-ab52-df9d4facdb8f"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="output_width",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["8b98969d-2345-4279-8bde-5be5c4003dbe"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="output_height",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["5be7b5fd-ce07-4713-ab27-28b87be7ca8c"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="batch_size",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["cae89f0d-c160-4fec-b5f4-b05e97a2bff3"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="temporal_overlap",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["565255dc-6ba6-4cfb-97af-78453a7023d4"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="randomize_seed",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["5e23daa1-16ae-4ed2-b799-e090b7318cad"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="seed",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["a765e3af-28dc-4399-a0e4-6964984b9714"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="output_file",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["e97f9192-9884-418b-a4af-d18f241838a9"],
                    initial_setup=True,
                    is_output=False,
                )
            )
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="was_successful",
                    node_name=node2_name,
                    value=top_level_unique_values_dict["5e23daa1-16ae-4ed2-b799-e090b7318cad"],
                    initial_setup=True,
                    is_output=False,
                )
            )
        with GriptapeNodes.ContextManager().node(node3_name):
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="note",
                    node_name=node3_name,
                    value=top_level_unique_values_dict["8fc12bba-3907-4f26-b521-68b8b5886c67"],
                    initial_setup=True,
                    is_output=False,
                )
            )
        with GriptapeNodes.ContextManager().node(node4_name):
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="note",
                    node_name=node4_name,
                    value=top_level_unique_values_dict["d923924c-2771-46e9-b26f-40fe9f487df2"],
                    initial_setup=True,
                    is_output=False,
                )
            )
        with GriptapeNodes.ContextManager().node(node5_name):
            await GriptapeNodes.ahandle_request(
                SetParameterValueRequest(
                    parameter_name="note",
                    node_name=node5_name,
                    value=top_level_unique_values_dict["0d17da4a-3e2a-4ed3-96de-973244afec63"],
                    initial_setup=True,
                    is_output=False,
                )
            )
