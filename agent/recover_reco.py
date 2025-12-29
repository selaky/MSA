from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
import recover_helper
import logging
import json

@AgentServer.custom_recognition("should_use_potion")
class ShouldUsePotion(CustomRecognition):
    def analyze(self, context:Context, argv:CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        return super().analyze(context, argv)
