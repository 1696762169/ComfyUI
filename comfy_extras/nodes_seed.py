from typing_extensions import override

from comfy_api.latest import ComfyExtension, io

class SimpleSeedNode(io.ComfyNode):
    @classmethod
    @override
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="SimpleSeedNode",
            display_name="Simple Seed",
            category="utils/seed",
            search_aliases=["seed", "random", "global seed", "master seed"],
            inputs=[
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    control_after_generate=io.ControlAfterGenerate.fixed,
                    tooltip="Master seed value supplied to all reachable nodes.",
                ),
            ],
            outputs=[
                io.Int.Output(display_name="seed"),
            ],
        )

    @classmethod
    @override
    def execute(cls, seed: int, **kwargs) -> io.NodeOutput:
        return io.NodeOutput(seed)

class SeedExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [SimpleSeedNode]


async def comfy_entrypoint() -> SeedExtension:
    return SeedExtension()
