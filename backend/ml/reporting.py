import os

def generate_html_report(
    metadata: dict,
    eda_stats: dict,
    ml_results: dict,
    charts: dict, # Now a dict of categories
    output_path: str,
    job_id: str,
    insights: str = ""
):
    """
    Combine YData Profiling Report with our AutoML, Insights, and Categorized Charts.
    """
    
    # 1. YData Report path
    ydata_path = output_path.replace('.html', '_profile.html')
    
    ydata_content = ""
    if os.path.exists(ydata_path):
        with open(ydata_path, 'r', encoding='utf-8') as f:
            ydata_content = f.read()
            
    # 2. Build Charts Section HTML
    charts_html = "<div style='margin-top: 30px;'>"
    
    for category, chart_list in charts.items():
        if not chart_list: continue # Skip empty categories
        
        # Unique ID for the summary details
        cat_id = category.replace(" ", "_").replace("&", "").replace("/", "")
        
        charts_html += f"""
        <details style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <summary style="padding: 15px; cursor: pointer; font-weight: 600; color: #111827; list-style: none; display: flex; align-items: center;">
                <span style="margin-right: 10px;">▶</span> {category}
            </summary>
            <div style="padding: 20px; border-top: 1px solid #e5e7eb; background: #f9fafb;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px;">
        """
        
        for chart in chart_list:
            if chart['path']:
                # The path is relative to 'static/charts/{job_id}/' usually, but here we just get the filename
                # We need to construct the full relative path for the HTML
                # output_path is like static/reports/report_ID.html
                # visuals are in static/charts/ID/
                # So src should be ../charts/{job_id}/{filename}
                img_src = f"../charts/{job_id}/{chart['path']}"
                charts_html += f"""
                    <div style="background: white; padding: 10px; border-radius: 6px; border: 1px solid #eee;">
                        <h4 style="margin: 0 0 10px 0; font-size: 0.9em; color: #6b7280;">{chart['title']}</h4>
        """
                
                # educational context for Histograms
                if "Histogram" in chart['title']:
                    charts_html += """
                        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 10px; margin-bottom: 10px; font-size: 0.85em; color: #1e40af;">
                            <strong>What is a Histogram?</strong> 
                            A histogram is a graph that shows the frequency of numerical data using rectangles. The height of each rectangle (bin) represents the number of data points that fall within that range.
                            <br/><br/>
                            <strong>What does it tell you?</strong>
                            It reveals the distribution (shape) of the data. You can see where most values lie (central tendency), how spread out they are (variation), and if the data is skewed (leaning left or right) or has outliers.
                        </div>
                    """

                charts_html += f"""
                        <img src="{img_src}" style="width: 100%; height: auto; border-radius: 4px;" loading="lazy" />
                    </div>
                """
            else:
                charts_html += f"""
                    <div style="padding: 10px; color: #6b7280; font-style: italic;">
                        {chart['title']}
                    </div>
                """
                
        charts_html += """
                </div>
            </div>
        </details>
        """
        
    charts_html += "</div>"

    # 3. Create Custom Header/Summary
    bg_color = metadata.get("backgroundColor", "#eef2ff")
    custom_section = f"""
    <div style="font-family: 'Inter', system-ui, -apple-system, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px;">
        <div style="background: {bg_color}; padding: 25px; border-radius: 12px; margin-bottom: 30px; border: 1px solid #c7d2fe;">
            <h1 style="color: #3730a3; margin-top: 0; font-size: 1.8rem;">🚀 AI Data Analysis Report</h1>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size: 0.85em; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">Target Variable</div>
                    <div style="font-weight: 600; color: #111827; font-size: 1.1em;">{ml_results.get('target_col', 'N/A')}</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size: 0.85em; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">Best Model</div>
                    <div style="font-weight: 600; color: #111827; font-size: 1.1em;">{str(ml_results.get('best_estimator', 'N/A'))}</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size: 0.85em; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">Accuracy / R2</div>
                    <div style="font-weight: 600; color: #059669; font-size: 1.1em;">{ml_results.get('metrics', {}).get('accuracy', ml_results.get('metrics', {}).get('r2', 'N/A'))}</div>
                </div>
            </div>
            
            <div style="margin-top: 25px;">
                <h3 style="color: #4338ca; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">🧠</span> AI Analyst Insights & Strategic Recommendations
                </h3>
                <div style="background: rgba(255,255,255,0.6); padding: 15px; border-radius: 8px; line-height: 1.6; color: #374151; white-space: pre-wrap; font-family: system-ui, -apple-system, sans-serif;">
                    {insights}
                </div>
            </div>
        </div>
        
        <h2 style="color: #111827; margin-bottom: 20px; font-size: 1.5rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">📊 Visual Analysis Gallery</h2>
        {charts_html}
        
        <div style="margin-top: 50px; text-align: center; color: #6b7280;">
             <p>Scroll down for detailed statistical profiling by YData.</p>
             <div style="font-size: 2rem;">⬇</div>
        </div>
    </div>
    """
        
    # 4. Inject into YData Report
    if "<body>" in ydata_content:
        # We need to inject stylings fordetails/summary interaction if needed, but default HTML5 is okay.
        final_html = ydata_content.replace(
            "<body>", 
            f"<body>{custom_section}"
        )
    else:
        final_html = f"<html><head><title>Analysis Report</title></head><body style='margin:0; background:#f3f4f6;'>{custom_section}</body></html>"
        
    # 5. Save Final Report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    return output_path
