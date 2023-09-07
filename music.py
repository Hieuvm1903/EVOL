from streamlit_player import st_player
import numpy as np
def demo(s):
    st_player(s)
music = np.array([["Wildside Beastar",'https://www.youtube.com/watch?v=bgo9dJB_icw'],
                  ["Another Love",'https://www.youtube.com/watch?v=MwpMEbgC7DA'],
                  ["Lần cuối",'https://www.youtube.com/watch?v=kSjj0LlsqnI'],
                  ["Can you?",'https://www.youtube.com/watch?v=QJJYpsA5tv8'],
                  ["The Rumbling",'https://www.youtube.com/watch?v=OBqw818mQ1E'],
                  ["",""]                 
                  ])
