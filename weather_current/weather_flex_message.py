# weather_flex_message.py

WEATHER_FLEX_MESSAGE = {
  "type": "bubble",
  "size": "mega",
  "body": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {
        "type": "text",
        "text": "📍 {location_name} 即時天氣",
        "color": "#000000",
        "weight": "bold",
        "size": "lg",
        "margin": "md",
        "align": "center"
      },
      {
        "type": "separator",
        "margin": "md"
      },
      {
        "type": "box",
        "layout": "vertical",
        "margin": "lg",
        "spacing": "sm",
        "contents": [
          {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {
                "type": "text",
                "text": "⏱️ 觀測時間:",
                "color": "#4169E1",
                "size": "md",
                "flex": 4
              },
              {
                "type": "text",
                "text": "2025-06-26 20:00",
                "wrap": True, # Python 使用 True 而非 true
                "color": "#8A2BE2",
                "size": "md",
                "flex": 5
              }
            ]
          },
          {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {
                "type": "text",
                "text": "🌈 天氣狀況:",
                "color": "#4169E1",
                "size": "md",
                "flex": 4
              },
              {
                "type": "text",
                "text": "多雲時晴",
                "wrap": True, # Python 使用 True 而非 true
                "color": "#8A2BE2",
                "size": "md",
                "flex": 5
              }
            ]
          },
          {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
              {
                "type": "box",
                "layout": "baseline",
                "contents": [
                  {
                    "type": "text",
                    "text": "🌡️ 溫度:",
                    "color": "#4169E1",
                    "size": "md",
                    "flex": 4
                  },
                  {
                    "type": "text",
                    "text": "28°C",
                    "wrap": True, # Python 使用 True 而非 true
                    "color": "#8A2BE2",
                    "size": "md",
                    "flex": 5
                  }
                ]
              },
              {
                "type": "box",
                "layout": "baseline",
                "contents": [
                  {
                    "type": "text",
                    "text": "          (體感溫度:",
                    "color": "#4169E1",
                    "size": "md",
                    "flex": 4
                  },
                  {
                    "type": "text",
                    "text": "28°C)",
                    "wrap": True, # Python 使用 True 而非 true
                    "color": "#8A2BE2",
                    "size": "md",
                    "flex": 5
                  }
                ]
              }
            ]
          },
          {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {
                "type": "text",
                "text": "💧 濕度:",
                "color": "#4169E1",
                "size": "md",
                "flex": 4
              },
              {
                "type": "text",
                "text": "75%",
                "wrap": True, # Python 使用 True 而非 true
                "color": "#8A2BE2",
                "size": "md",
                "flex": 5
              }
            ]
          },
          {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {
                "type": "text",
                "text": "🌧️ 降雨量:",
                "color": "#4169E1",
                "size": "md",
                "flex": 4
              },
              {
                "type": "text",
                "text": "5 mm",
                "wrap": True, # Python 使用 True 而非 true
                "color": "#8A2BE2",
                "size": "md",
                "flex": 5
              }
            ]
          },
          {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
              {
                "type": "box",
                "layout": "baseline",
                "contents": [
                  {
                    "type": "text",
                    "text": "🌬️ 風速:",
                    "color": "#4169E1",
                    "size": "md",
                    "flex": 4
                  },
                  {
                    "type": "text",
                    "text": "3 m/s",
                    "wrap": True, # Python 使用 True 而非 true
                    "color": "#8A2BE2",
                    "size": "md",
                    "flex": 5
                  }
                ]
              },
              {
                "type": "box",
                "layout": "baseline",
                "contents": [
                  {
                    "type": "text",
                    "text": "          (風向:",
                    "color": "#4169E1",
                    "size": "md",
                    "flex": 4
                  },
                  {
                    "type": "text",
                    "text": "東北)",
                    "wrap": True, # Python 使用 True 而非 true
                    "color": "#8A2BE2",
                    "size": "md",
                    "flex": 5
                  }
                ]
              }
            ]
          },
          {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {
                "type": "text",
                "text": "🧭 氣壓:",
                "color": "#4169E1",
                "size": "md",
                "flex": 4
              },
              {
                "type": "text",
                "text": "1012 hPa",
                "wrap": True, # Python 使用 True 而非 true
                "color": "#8A2BE2",
                "size": "md",
                "flex": 5
              }
            ]
          },
          {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {
                "type": "text",
                "text": "☀️ 紫外線指數:",
                "color": "#4169E1",
                "size": "md",
                "flex": 4
              },
              {
                "type": "text",
                "text": "7 (高)",
                "wrap": True, # Python 使用 True 而非 true
                "color": "#8A2BE2",
                "size": "md",
                "flex": 5
              }
            ]
          }
        ]
      },
      {
        "type": "separator",
        "margin": "md"
      },
      {
        "type": "text",
        "text": "--- 資訊僅供參考，請以中央氣象署最新發布為準 ---",
        "size": "md",
        "color": "#808080",
        "wrap": True, # Python 使用 True 而非 true
        "margin": "md",
        "align": "center"
      }
    ]
  }
}