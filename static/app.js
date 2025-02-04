// static/app.js

function getSuggestion() {
    // 位置情報を取得
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(successCallback, errorCallback);
    } else {
      alert("お使いのブラウザでは位置情報が使用できません。");
    }
  
    function successCallback(position) {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
  
      // サーバーへPOST
      fetch("/get_suggestion", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `lat=${lat}&lon=${lon}`
      })
        .then((res) => res.json())
        .then((data) => {
          const suggestionBox = document.getElementById("suggestion-result");
          if (data.error) {
            suggestionBox.innerHTML = `<p style="color:red;">${data.error}</p>`;
            suggestionBox.style.display = "block";
          } else {
            let html = `<p>${data.suggestion_text}</p>`;
            if (data.image_url) {
              html += `<img src="${data.image_url}" alt="提案画像">`;
            }
            html += `
              <div style="margin-top:10px;">
                <button onclick="addFavorite('${encodeURIComponent(data.suggestion_text)}', '${encodeURIComponent(data.image_url || "")}')">
                  お気に入りに追加
                </button>
              </div>
            `;
            suggestionBox.innerHTML = html;
            suggestionBox.style.display = "block";
          }
        })
        .catch((err) => {
          alert("提案の取得に失敗しました。");
          console.error(err);
        });
    }
  
    function errorCallback(error) {
      alert("位置情報の取得が許可されませんでした。");
      console.error(error);
    }
  }
  
  function addFavorite(suggestionText, imageUrl) {
    // お気に入りに追加
    fetch("/add_favorite", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: `suggestion_text=${suggestionText}&image_url=${imageUrl}`
    })
      .then((res) => res.text())
      .then((data) => {
        alert(data);
      })
      .catch((err) => {
        alert("お気に入り登録に失敗しました。");
        console.error(err);
      });
  }
  
  