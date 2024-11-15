import matplotlib.pyplot as plt
import networkx as nx

# 그래프 생성
G = nx.DiGraph()

# 노드 추가
G.add_nodes_from([
    "DATA_COLLECTION_PREFETCH_AGENT",
    "DATA_COLLECTION_EVENT_LOG_AGENT",
    "DATA_SAVE_AGENT",
    "DATA_SEARCH_AGENT",
    "DATA_ANALYSIS_AGENT",
    "DATA_VISUALIZATION_AGENT",
    "TEAM_SUPERVISOR"
])

# 엣지 추가
G.add_edges_from([
    ("DATA_COLLECTION_PREFETCH_AGENT", "DATA_SAVE_AGENT"),
    ("DATA_COLLECTION_EVENT_LOG_AGENT", "DATA_SAVE_AGENT"),
    ("DATA_SAVE_AGENT", "DATA_SEARCH_AGENT"),
    ("DATA_SEARCH_AGENT", "TEAM_SUPERVISOR"),
    ("TEAM_SUPERVISOR", "DATA_VISUALIZATION_AGENT")
])

# 그래프 시각화
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, arrows=True)
plt.show()
