document.addEventListener('DOMContentLoaded', async () => {
    const teamNameInput = document.getElementById('team-name');
    const newItemInput = document.getElementById('new-item');
    const addItemForm = document.getElementById('add-item-form');
    const todoList = document.getElementById('todo-list');
    const progressText = document.getElementById('progress-text');
    const progressBar = document.getElementById('progress-bar');
    const recommendationsContainer = document.getElementById('recommendations');

    const attractionRecommendations = [
        { id: 'rec-1', text: '혜성특급 타기' },
        { id: 'rec-2', text: '자이로드롭 도전!' },
        { id: 'rec-3', text: '후룸라이드 타고 시원하게' },
    ];

    const foodRecommendations = [
        { id: 'rec-4', text: '구슬 아이스크림 먹기' },
        { id: 'rec-5', text: '츄러스 사먹기' },
    ];

    const showRecommendations = [
        { id: 'rec-6', text: '가든 스테이지 공연 보기' },
        { id: 'rec-7', text: '로티스 어드벤처 퍼레이드 구경' },
    ];
    const allRecommendations = [...attractionRecommendations, ...foodRecommendations, ...showRecommendations];

    // --- Firebase Setup ---
    const firebaseConfig = {
        databaseURL: "https://ourlotteday-default-rtdb.asia-southeast1.firebasedatabase.app",
    };
    // Initialize Firebase only if it hasn't been initialized yet
    if (!firebase.apps.length) {
        firebase.initializeApp(firebaseConfig);
    }
    const database = firebase.database();
    const DB_PATH = '/our-lotte-day';
    const dbRef = database.ref(DB_PATH);
    const todosRef = dbRef.child('todos');

    let todos = [];
    let currentTodoId = null;
    const photoUploadInput = document.getElementById('photo-upload');

    const initializeDefaultTodos = () => {
        allRecommendations.forEach((rec, index) => {
            todosRef.push({ text: rec.text, completed: false, order: index });
        });
    };

    const initializeDefaultData = () => {
        dbRef.child('teamName').set('✨ 우리들의 신나는 모험 ✨');
        initializeDefaultTodos();
    };

    const updateTeamName = (name) => {
        dbRef.child('teamName').set(name);
    };

    // --- Core Rendering Functions ---
    const renderEmptyList = () => {
        if (todoList.children.length === 0) {
            todoList.innerHTML = ''; // Clear any existing message
            const emptyMsg = document.createElement('li');
            emptyMsg.className = 'list-group-item text-center text-muted';
            emptyMsg.textContent = '모든 임무 완료! 🎉';
            todoList.appendChild(emptyMsg);
            return;
        }

        // If there are items, ensure the empty message is removed
        const emptyMsg = todoList.querySelector('.text-muted');
        if (emptyMsg) emptyMsg.remove();
    };

    const renderTodoItem = (todo) => {
        const li = document.createElement('li');
        li.className = `list-group-item ${todo.completed ? 'completed' : ''}`;
        li.dataset.id = todo.id;
        li.dataset.order = todo.order;

        const topRow = document.createElement('div');
        topRow.className = 'todo-top-row';

        const handle = document.createElement('span');
        handle.className = 'drag-handle';
        handle.innerHTML = '&#9776;';
        handle.addEventListener('mousedown', startDrag);
        handle.addEventListener('touchstart', startDrag);

        const textSpan = document.createElement('span');
        textSpan.className = 'todo-text';
        textSpan.textContent = todo.text;
        textSpan.addEventListener('click', () => toggleTodo(todo.id, !todo.completed));

        const rightContainer = document.createElement('div');
        rightContainer.className = 'right-container';

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-danger btn-sm';
        deleteBtn.textContent = 'X';
        deleteBtn.addEventListener('click', () => deleteTodo(todo.id));

        if (todo.completed) {
            if (todo.imageUrl) {
                // 이미지가 있을 경우: 교체 및 삭제 버튼
                const replaceBtn = document.createElement('button');
                replaceBtn.className = 'btn btn-sm btn-outline-success upload-btn me-1';
                replaceBtn.textContent = '사진 교체';
                replaceBtn.onclick = () => {
                    currentTodoId = todo.id;
                    photoUploadInput.click();
                };
                const deletePhotoBtn = document.createElement('button');
                deletePhotoBtn.className = 'btn btn-sm btn-outline-danger upload-btn';
                deletePhotoBtn.textContent = '사진 삭제';
                deletePhotoBtn.onclick = () => deletePhoto(todo.id);
                rightContainer.appendChild(replaceBtn);
                rightContainer.appendChild(deletePhotoBtn);
            } else {
                // 이미지가 없을 경우: 업로드 버튼
                const uploadBtn = document.createElement('button');
                uploadBtn.className = 'btn btn-sm btn-outline-primary upload-btn';
                uploadBtn.textContent = '사진 올리기';
                uploadBtn.onclick = () => {
                    currentTodoId = todo.id;
                    photoUploadInput.click();
                };
                rightContainer.appendChild(uploadBtn);
            }
        }

        rightContainer.appendChild(deleteBtn);

        topRow.appendChild(handle);
        topRow.appendChild(textSpan);
        topRow.appendChild(rightContainer);

        li.appendChild(topRow);

        if (todo.completed && todo.imageUrl) {
            const img = document.createElement('img');
            img.src = todo.imageUrl;
            img.className = 'todo-image';
            li.appendChild(img);
        }

        return li;
    };

    let draggedItem = null;
    let isDragging = false;

    function startDrag(e) {
        // Prevent text selection while dragging
        e.preventDefault();
        isDragging = true;
        draggedItem = e.target.closest('li');
        draggedItem.classList.add('dragging');

        document.addEventListener('mousemove', onDrag);
        document.addEventListener('touchmove', onDrag, { passive: false });

        document.addEventListener('mouseup', endDrag);
        document.addEventListener('touchend', endDrag, { passive: true });
    }

    function onDrag(e) {
        if (!isDragging || !draggedItem) return;
        e.preventDefault();

        const y = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;
        const afterElement = getDragAfterElement(todoList, y);

        if (afterElement == null) {
            todoList.appendChild(draggedItem);
        } else {
            todoList.insertBefore(draggedItem, afterElement);
        }
    }

    function endDrag() {
        if (!isDragging || !draggedItem) return;
        isDragging = false;
        if (draggedItem) {
            draggedItem.classList.remove('dragging');
        }

        document.removeEventListener('mousemove', onDrag);
        document.removeEventListener('touchmove', onDrag);
        document.removeEventListener('mouseup', endDrag);
        document.removeEventListener('touchend', endDrag);

        updateTodosOrder();
        draggedItem = null;
    }

    const getDragAfterElement = (container, y) => {
        const draggableElements = [...container.querySelectorAll('li:not(.dragging)')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    };

    const updateTodosOrder = () => {
        const newOrderedIds = [...todoList.querySelectorAll('li')].map(li => li.dataset.id);
        if (newOrderedIds.length !== todos.length) return; // Avoid updates on empty or partial lists

        const newTodos = newOrderedIds.map((id, index) => {
            const todo = todos.find(t => t.id === id);
            return { ...todo, order: index };
        });
        todos = newTodos;

        const updates = {};
        todos.forEach(todo => {
            if(todo.id) {
                updates[`${DB_PATH}/todos/${todo.id}/order`] = todo.order;
            }
        });
        if (Object.keys(updates).length > 0) {
            database.ref().update(updates);
        }
    };

    const updateProgress = () => {
        const completedCount = todos.filter(todo => todo.completed).length;
        const totalCount = todos.length;
        const percentage = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

        progressText.textContent = `달성률: ${Math.round(percentage)}% (${completedCount}/${totalCount})`;
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);

        // --- Milestone Celebration ---
        maybeCelebrateMilestone(percentage, totalCount);
    };

    const addTodo = (text) => {
        if (text.trim() === '') return;
        const newTodo = { text: text.trim(), completed: false, order: todos.length };
        todosRef.push(newTodo);
    };

    const toggleTodo = (id, isCompleted) => {
        todosRef.child(`${id}/completed`).set(isCompleted);
    };

    const deleteTodo = (id) => {
        todosRef.child(id).remove();
    };

    const deletePhoto = (id) => {
        if (confirm('정말로 사진을 삭제하시겠습니까?')) {
            todosRef.child(`${id}/imageUrl`).remove();
        }
    };

    const restoreUploadButtons = (buttons, spinner) => {
        spinner.remove();
        buttons.forEach(btn => {
            const originalDisplay = btn.dataset.prevDisplay;
            btn.style.display = originalDisplay !== undefined ? originalDisplay : '';
            delete btn.dataset.prevDisplay;
        });
    };

    const uploadPhoto = (file) => {
        if (!currentTodoId || !file) return;

        // 1. 로딩 스피너를 표시할 li 요소를 찾습니다.
        const listItem = document.querySelector(`li[data-id="${currentTodoId}"]`);
        if (!listItem) return;

        const rightContainer = listItem.querySelector('.right-container');
        const uploadButtons = rightContainer ? Array.from(rightContainer.querySelectorAll('.upload-btn')) : [];

        // 2. 스피너 엘리먼트를 생성합니다.
        const spinner = document.createElement('div');
        spinner.className = 'spinner-border spinner-border-sm text-primary me-2'; // me-2로 오른쪽 여백 추가
        spinner.setAttribute('role', 'status');
        spinner.innerHTML = `<span class="visually-hidden">Loading...</span>`;

        // 3. 기존 버튼을 숨기고 스피너를 표시합니다.
        uploadButtons.forEach(btn => {
            btn.dataset.prevDisplay = btn.style.display;
            btn.style.display = 'none';
        });
        if (rightContainer) {
            rightContainer.prepend(spinner);
        }

        // --- 이미지 리사이징 로직 시작 ---
        const MAX_WIDTH = 800; // 이미지 최대 가로 크기
        const reader = new FileReader(); // 파일을 읽기 위한 FileReader

        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target.result;

            img.onload = () => {
                const canvas = document.createElement('canvas');
                let width = img.width;
                let height = img.height;

                // 가로 크기가 MAX_WIDTH보다 크면 비율에 맞게 줄임
                if (width > MAX_WIDTH) {
                    height *= MAX_WIDTH / width;
                    width = MAX_WIDTH;
                }

                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                // canvas의 이미지를 JPEG 데이터 URL로 변환 (품질 70%)
                const resizedImageUrl = canvas.toDataURL('image/jpeg', 0.7);

                // 리사이징된 이미지를 Firebase에 업로드
              
                todosRef.child(`${currentTodoId}/imageUrl`).set(resizedImageUrl)
                    .then(() => {
                        currentTodoId = null; // 성공 시 ID 초기화
                    })
                    .catch(error => {
                        alert('데이터베이스에 사진을 저장하지 못했습니다: ' + error.message);
                        currentTodoId = null;
                    })
                    .finally(() => {
                        // 4. 통신이 끝나면 스피너를 제거하고, 버튼을 다시 보이게 합니다.
                        restoreUploadButtons(uploadButtons, spinner);
                    });
            };
        };

        reader.onerror = (error) => { // 파일 읽기 실패 시
            console.error("Error reading file:", error);
            alert("파일을 읽는 중 오류가 발생했습니다.");
            // 에러 발생 시 스피너를 제거하고, 숨겨둔 버튼을 다시 보이게 합니다.
            restoreUploadButtons(uploadButtons, spinner);
            currentTodoId = null;
        };

        reader.readAsDataURL(file);

    };

    // --- Event Listeners ---
    addItemForm.addEventListener('submit', e => {
        e.preventDefault();
        addTodo(newItemInput.value);
        newItemInput.value = '';
    });

    let debounceTimeout;
    teamNameInput.addEventListener('input', () => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            updateTeamName(teamNameInput.value);
        }, 500);
    });

    photoUploadInput.addEventListener('change', e => {
        const file = e.target.files[0];
        uploadPhoto(file);
    });
    allRecommendations.forEach(rec => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-sm m-1';
        btn.textContent = rec.text;
        btn.onclick = () => addTodo(rec.text);
        recommendationsContainer.appendChild(btn);
    });

    // --- Efficient Data Listeners ---
    dbRef.child('teamName').on('value', (snapshot) => {
        teamNameInput.value = snapshot.val() || '✨ 우리들의 신나는 모험 ✨';
    });

    todosRef.on('child_added', (snapshot) => {
        const newTodo = { id: snapshot.key, ...snapshot.val() };
        todos.push(newTodo);
        todos.sort((a, b) => a.order - b.order); // Keep the array sorted

        const newItemElement = renderTodoItem(newTodo);

        // Find the correct position to insert the new item based on its order
        const existingItems = Array.from(todoList.children);
        const successor = existingItems.find(item => parseInt(item.dataset.order) > newTodo.order);

        if (successor) {
            todoList.insertBefore(newItemElement, successor);
        } else {
            todoList.appendChild(newItemElement);
        }
        renderEmptyList();
        updateProgress();
    });

    todosRef.on('child_changed', (snapshot) => {
        const changedTodo = { id: snapshot.key, ...snapshot.val() };
        const index = todos.findIndex(t => t.id === changedTodo.id);
        if (index > -1) {
            todos[index] = changedTodo;
            const oldItemElement = todoList.querySelector(`li[data-id="${changedTodo.id}"]`);
            if (oldItemElement) {
                const newItemElement = renderTodoItem(changedTodo);
                oldItemElement.replaceWith(newItemElement);
                updateProgress();
            }
        }
    });

    todosRef.on('child_removed', (snapshot) => {
        todos = todos.filter(t => t.id !== snapshot.key);
        todoList.querySelector(`li[data-id="${snapshot.key}"]`)?.remove();
        renderEmptyList();
        updateProgress();
    });

    // ==========================
    // Milestone Celebration Utils
    // ==========================
    const milestones = [25, 50, 75, 100];
    let lastCelebratedMilestone = 0;

    function maybeCelebrateMilestone(percentage, totalCount) {
        if (totalCount === 0) return;
        const next = milestones.find(m => percentage >= m && lastCelebratedMilestone < m);
        if (!next) return;
        lastCelebratedMilestone = next;
        celebrate(next);
    }

    function celebrate(level) {
        // Visual celebration only (no vibration/sound)
        spawnEmojiConfetti(level);
    }

    function spawnEmojiConfetti(level) {
        const count = level === 100 ? 40 : level === 75 ? 28 : level === 50 ? 22 : 16;
        const emojis = ['🎉', '✨', '💖', '⭐', '🎈'];
        const duration = 1500;
        for (let i = 0; i < count; i++) {
            const span = document.createElement('span');
            span.className = 'confetti-emoji';
            span.textContent = emojis[Math.floor(Math.random() * emojis.length)];
            const startLeft = Math.random() * 100; // vw
            const size = 16 + Math.random() * 20; // px
            const rotate = Math.random() * 360;
            const delay = Math.random() * 200; // ms
            span.style.left = startLeft + 'vw';
            span.style.fontSize = size + 'px';
            span.style.transform = `rotate(${rotate}deg)`;
            span.style.animationDuration = (1 + Math.random() * 0.6) + 's';
            span.style.animationDelay = delay + 'ms';
            document.body.appendChild(span);
            setTimeout(() => span.remove(), duration + 600);
        }
    }

    // Removed sound (playChime) and vibration for mobile compatibility

});
