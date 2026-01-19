def calculate_reward(performance, user_feedback):
    return (performance.alpha * 0.6 + user_feedback * 0.4)
