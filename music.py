from streamlit_player import st_player
import numpy as np
def demo(s):
    st_player(s)
music = np.array(['https://www.youtube.com/watch?v=bgo9dJB_icw',
                  'https://www.youtube.com/watch?v=MwpMEbgC7DA',
                  'https://www.youtube.com/watch?v=kSjj0LlsqnI',
                  'https://www.youtube.com/watch?v=QJJYpsA5tv8',
                  'https://www.youtube.com/watch?v=OBqw818mQ1E',
                  ''                  
                  ])
