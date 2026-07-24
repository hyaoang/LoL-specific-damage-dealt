import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.patches import Polygon

# ================= Configuration =================
API_KEY = ""  # Your API Key
id = input("your ID: ")
MATCH_ID = (
    "TW2_"+id  # Your Game ID (note the region prefix, TW server is usually TW2)
)
REGION_ROUTE = "sea"
RELATIVE_COLOR_MODE = True  # True: 根據該英雄對五名敵人的傷害分佈著色; False: 根據全場最高傷害著色
# ===========================================


def get_match_data(api_key, match_id, region):
    headers = {"X-Riot-Token": api_key, "User-Agent": "HoHoHo"}

    # 1. Get champion names
    url_match = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    print("Downloading match data...")
    resp_match = requests.get(url_match, headers=headers)

    if resp_match.status_code != 200:
        print(f"[Error] Failed to fetch match data!")
        print(f"Status Code: {resp_match.status_code}")
        print(f"Request URL: {url_match}")
        print(f"Server Response: {resp_match.text}")
        return None

    participants = resp_match.json()["info"]["participants"]
    id_to_champ = {p["participantId"]: p["championName"] for p in participants}

    # 2. Get timeline data
    url_timeline = (
        f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    )
    print("Downloading timeline data...")
    resp_timeline = requests.get(url_timeline, headers=headers)

    if resp_timeline.status_code != 200:
        print(f"[Error] Failed to fetch timeline data!")
        print(f"Status Code: {resp_timeline.status_code}")
        print(f"Request URL: {url_timeline}")
        print(f"Server Response: {resp_timeline.text}")
        return None

    timeline_data = resp_timeline.json()

    # Initialize matrices
    blue_dmg_matrix = np.zeros((5, 5))  # Blue hits Red
    red_dmg_matrix = np.zeros((5, 5))  # Red hits Blue

    for frame in timeline_data["info"]["frames"]:
        for event in frame["events"]:
            if event["type"] == "CHAMPION_KILL":
                victim_id = event["victimId"]

                if "victimDamageReceived" in event:
                    for dmg_info in event["victimDamageReceived"]:
                        attacker_id = dmg_info["participantId"]
                        if attacker_id == 0:
                            continue  # Ignore towers/minions

                        dmg = (
                            dmg_info.get("magicDamage", 0)
                            + dmg_info.get("physicalDamage", 0)
                            + dmg_info.get("trueDamage", 0)
                        )

                        # Blue team (1-5) hits Red team (6-10)
                        if 1 <= attacker_id <= 5 and 6 <= victim_id <= 10:
                            blue_dmg_matrix[attacker_id - 1][victim_id - 6] += dmg

                        # Red team (6-10) hits Blue team (1-5)
                        elif 6 <= attacker_id <= 10 and 1 <= victim_id <= 5:
                            red_dmg_matrix[victim_id - 1][attacker_id - 6] += dmg

    return id_to_champ, blue_dmg_matrix, red_dmg_matrix


def format_to_k(val):
    if val == 0:
        return "0"
    return f"{val / 1000:.1f}K"


def plot_split_triangles(id_to_champ, blue_matrix, red_matrix, relative_color_mode=False):
    if blue_matrix is None:
        return

    blue_champs = [id_to_champ[i] for i in range(1, 6)]
    red_champs = [id_to_champ[i] for i in range(6, 11)]

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_aspect("equal")  # Ensure each grid cell is a square

    # Set color mapping and global normalization
    global_blue_max = blue_matrix.max() if blue_matrix.max() > 0 else 1
    global_red_max = red_matrix.max() if red_matrix.max() > 0 else 1
    global_blue_norm = plt.Normalize(0, global_blue_max)
    global_red_norm = plt.Normalize(0, global_red_max)
    blue_cmap = plt.get_cmap("Blues")
    red_cmap = plt.get_cmap("Reds")

    # Draw triangles
    for i in range(5):  # Y-axis (Blue team champions)
        for j in range(5):  # X-axis (Red team champions)
            # Coordinates of the four vertices of each cell
            tl = (j - 0.5, i - 0.5)  # Top-Left
            tr = (j + 0.5, i - 0.5)  # Top-Right
            bl = (j - 0.5, i + 0.5)  # Bottom-Left
            br = (j + 0.5, i + 0.5)  # Bottom-Right

            b_val = blue_matrix[i, j]
            r_val = red_matrix[i, j]

            # 根據模式決定色彩正規化的基準
            if relative_color_mode:
                # 藍隊第i位成員攻擊紅隊5人的最高傷害(列)
                b_row_max = blue_matrix[i, :].max()
                b_max = b_row_max if b_row_max > 0 else 1
                b_norm = plt.Normalize(0, b_max)

                # 紅隊第j位成員攻擊藍隊5人的最高傷害(行)
                r_col_max = red_matrix[:, j].max()
                r_max = r_col_max if r_col_max > 0 else 1
                r_norm = plt.Normalize(0, r_max)
            else:
                b_norm = global_blue_norm
                r_norm = global_red_norm

            # Top-Left triangle: Blue hits Red (vertices: Top-Left, Top-Right, Bottom-Left)
            poly_blue = Polygon(
                [tl, tr, bl],
                facecolor=blue_cmap(b_norm(b_val)),
                edgecolor="white",
                linewidth=1,
            )
            ax.add_patch(poly_blue)

            # Bottom-Right triangle: Red hits Blue (vertices: Top-Right, Bottom-Right, Bottom-Left)
            poly_red = Polygon(
                [tr, br, bl],
                facecolor=red_cmap(r_norm(r_val)),
                edgecolor="white",
                linewidth=1,
            )
            ax.add_patch(poly_red)

            # Determine font color based on background color intensity to ensure readability
            b_color = "white" if b_norm(b_val) > 0.5 else "black"
            r_color = "white" if r_norm(r_val) > 0.5 else "black"

            # Write Blue team damage text in the top-left
            ax.text(
                j - 0.15,
                i - 0.15,
                format_to_k(b_val),
                ha="center",
                va="center",
                color=b_color,
                fontsize=9,
                fontweight="bold",
            )
            # Write Red team damage text in the bottom-right
            ax.text(
                j + 0.15,
                i + 0.15,
                format_to_k(r_val),
                ha="center",
                va="center",
                color=r_color,
                fontsize=9,
                fontweight="bold",
            )

    # Set axis limits and direction
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(4.5, -0.5)  # Invert Y-axis so the first champion is at the top

    # Label settings
    ax.set_xticks(np.arange(5))
    ax.set_yticks(np.arange(5))

    # 修改為水平擺放(rotation=0)與置中(ha="center")
    ax.set_xticklabels(red_champs, rotation=0, ha="center", color="red", fontsize=11)
    ax.set_yticklabels(blue_champs, color="blue", fontsize=11)

    ax.set_xlabel("Red Team", fontsize=12)
    ax.set_ylabel("Blue Team", fontsize=12)

    ax.set_title(
        "Lethal Damage\nGame ID: "+MATCH_ID,
        fontsize=14,
        pad=20,
    )

    plt.tight_layout()
    plt.show()


# --- Execution ---
if __name__ == "__main__":
    data = get_match_data(API_KEY, MATCH_ID, REGION_ROUTE)
    if data:
        id_map, b_mat, r_mat = data
        plot_split_triangles(id_map, b_mat, r_mat, relative_color_mode=RELATIVE_COLOR_MODE)
    else:
        print("Cannot plot the chart because data fetching failed.")
