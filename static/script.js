// Waiting Room elements
const waitingRoomPage = document.getElementById('waiting-room-page');
const userIdDisplay = document.getElementById('user-id');
const positionDisplay = document.getElementById('position');
const totalUsersDisplay = document.getElementById('total-users');
const usersAheadDisplay = document.getElementById('users-ahead');
const estimatedWaitDisplay = document.getElementById('estimated-wait');
const waitingListDisplay = document.getElementById('waiting-list');

// Haven elements (will be accessed in haven.html)
let timeRemaining;
let havenKey;

let userId = localStorage.getItem('userId');
let aliveInterval;

// Function to get user ID from the server
async function getUserId() {
    try {
        const response = await fetch('/hi');
        const data = await response.json();
        userId = data.user_id;
        localStorage.setItem('userId', userId);
        userIdDisplay.textContent = userId;
        console.log('Assigned user ID:', userId);
    } catch (error) {
        console.error('Error getting user ID:', error);
    }
}

// Function to send 'alive' signal to the server
async function sendAlive() {
    try {
        const response = await fetch('/alive', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await response.json();
        if (data.status === 300) {
            // If not in waiting room or haven, get a new user ID
            await getUserId();
        }
    } catch (error) {
        console.error('Error sending alive signal:', error);
    }
}

// Function to get position and other queue information
async function getPosition() {
    try {
        const response = await fetch('/pos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await response.json();
        if (data.status === 300) {
            await getUserId();
            return;
        }

        positionDisplay.textContent = data.position;
        totalUsersDisplay.textContent = data.total;
        usersAheadDisplay.textContent = data.ahead;
        estimatedWaitDisplay.textContent = formatTime(data.estimated_wait);

        // Check if waiting_list exists in the data before updating the list
        if (data.waiting_list) {
            waitingListDisplay.innerHTML = '';
            for (const userId of data.waiting_list) {
                const listItem = document.createElement('li');
                listItem.textContent = userId;
                waitingListDisplay.appendChild(listItem);
            }
        }

        if (data.position === 1) {
            attemptEnterHaven();
        }
    } catch (error) {
        console.error('Error getting position:', error);
    }
}

// Function to attempt entering the haven
async function attemptEnterHaven() {
    try {
        const response = await fetch('/haven', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await response.json();
        if (response.ok) {
            havenKey = data.haven_key;
            localStorage.setItem('havenKey', havenKey); // Store havenKey in local storage
            window.location.href = '/haven.html';
        } else {
            console.error('Access to haven denied:', response.status);
        }
    } catch (error) {
        console.error('Error entering haven:', error);
    }
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60); // Round down to whole seconds
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
}
// Initial setup (only for index.html - waiting room)
if (window.location.pathname === '/') {
    if (!userId) {
        getUserId();
    } else {
        userIdDisplay.textContent = userId;
    }

    setInterval(sendAlive, 500);
    setInterval(getPosition, 1000);
}

// haven.html specific JavaScript

// Wrap haven-specific code in DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', (event) => {
    if (window.location.pathname === '/haven.html') {
        timeRemaining = document.getElementById('time-remaining');
        havenKey = localStorage.getItem('havenKey');

        setInterval(() => {
            fetch('/haven_alive', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ haven_key: havenKey })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 200) {
                    timeRemaining.textContent = formatTime(data.time_left);
                } else {
                    window.location.href = '/';
                }
            })
            .catch(error => {
                console.error('Error sending haven_alive signal:', error);
            });
        }, 300);
    }
});