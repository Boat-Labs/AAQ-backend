class AgentPolicy:
    def __init__(self, policy_id: str):
        self.policy_id = policy_id

    def choose_action(self, state):
        return "hold"
