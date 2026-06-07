import os
from src.graph import build_review_graph

def save_graph_image():
    print("Building graph...")
    app = build_review_graph()
    
    print("Generating image bytes via Mermaid...")
    try:
        # get_graph() extracts the state graph, draw_mermaid_png() renders it
        image_bytes = app.get_graph().draw_mermaid_png()
        
        output_path = "graph_architecture.png"
        
        # Write the binary data directly to a standard image file
        with open(output_path, "wb") as f:
            f.write(image_bytes)
            
        print(f"✅ Success! Graph image saved to {output_path}")
        
    except Exception as e:
        print(f"❌ Failed to generate graph image. Error: {e}")
        print("Note: This feature requires internet access as it uses the Mermaid API by default.")

if __name__ == "__main__":
    save_graph_image()