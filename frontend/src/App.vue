<template>
  <div id="app">
    <el-container>
      <el-header>
        <h1>Tello Face Drone Controller</h1>
      </el-header>
      <el-main>
        <el-row>
          <el-col :span="14">
            <el-card class="video-card" shadow="always">
              <el-image :src="BASE_URL + '/video_feed'">
                <div slot="placeholder" class="no-image-slot">
                  Setting up Video Stream…
                </div>
                <div slot="error" class="no-image-slot">
                  <i class="el-icon-error"></i>
                </div>
              </el-image>
            </el-card>
          </el-col>
          <el-col :span="10">
            <el-card :loading="!connected" class="controls-card" shadow="always">
              <div slot="header">
                <h5>Controls</h5>
              </div>

              <div class="category battery-level">
                <h5>Battery</h5>
                <el-progress :percentage="batteryPercent" :color="batteryColors" ></el-progress>
              </div>

              <div class="category speed-tags">
                <h5>Speed</h5>
                <el-tag class="speed-tag" :type="speedColor(speedLeftRight)">X {{ speedLeftRight }}</el-tag>
                <el-tag class="speed-tag" :type="speedColor(speedUpDown)">Y {{ speedUpDown }}</el-tag>
                <el-tag class="speed-tag" :type="speedColor(speedForBack)">Z {{ speedForBack }}</el-tag>
                <el-tag class="speed-tag" :type="speedColor(speedYaw)">α {{ speedYaw }}</el-tag>
              </div>

              <div class="category flight-control">
                <h5>Flight Control</h5>
                <el-row>
                  <el-button
                    icon="el-icon-upload2"
                    type="danger" round
                    :disabled="flying"
                    @click="setFlight(true)">Take Off</el-button>

                  <el-button
                    icon="el-icon-download"
                    type="success" round
                    :disabled="!flying"
                    @click="setFlight(false)">Land</el-button>
                </el-row>
              </div>

              <div class="category autonomous-control">
                <el-switch
                  v-model="autonomous"
                  active-color="#13ce66"
                  inactive-color="#ff4949"
                  active-text="Navigate Autonomously"
                  inactive-text="Override Navigation">
                </el-switch>
                <div class="spacer"></div>
                <el-switch
                  v-model="targetMode"
                  :disabled="!autonomous"
                  active-color="#13ce66"
                  inactive-color="#ff4949"
                  active-text="Target Mode"
                  inactive-text="Enroll Mode">
                </el-switch>
              </div>

            </el-card>

            <el-card class="friends-card" shadow="always">
              <div slot="header">
                <h5>Friends</h5>
                <el-button type="danger" icon="el-icon-close" size="small" circle @click="targetFace = ''"></el-button>  
                <div class="friends-list">
                  <div 
                    class="friends-list__item"
                    v-for="(face, index) in faces" :key="index"
                    :class="{active: targetFace === face}"
                    @click="targetFace = face"
                  >
                    <img :src="BASE_URL + '/faces/' + face" />
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script>
const v_directional = 50
const v_yaw_pitch = 100

export default {
  name: 'app',
  data () {
    return {
      BASE_URL: 'http://127.0.0.1:5000',
      batteryColors: [
        { color: '#f56c6c', percentage: 20 },
        { color: '#e6a23c', percentage: 40 },
        { color: '#5cb87a', percentage: 60 },
        { color: '#1989fa', percentage: 80 },
        { color: '#6f7ad3', percentage: 100 }
      ],
      batteryPercent: 0,
      speedForBack: 0,
      speedLeftRight: 0,
      speedUpDown: 0,
      speedYaw: 0,
      flying: false,
      autonomous: true,
      targetMode: true,
      connected: false,
      faces: [],
      targetFace: ''
    }
  },
  methods: {
    formatSpeed (percentage) {
      return `${percentage}`
    },
    speedColor (speed) {
      if (speed < 0) return 'danger'
      else if (speed > 0) return 'success'
      else return 'info'
    },
    setFlight (flying) {
      if (flying) {
        this.sendDroneCommand({
          command: 'take_off'
        })
        this.flying = true
      } else {
        this.sendDroneCommand({
          command: 'land'
        })
        this.flying = false
      }
    },
    sendDroneCommand (command) {
      this.$http.post(this.BASE_URL + '/drone_command', command).then(response => {
      }, response => {
        console.error(response)
      })
    }
  },
  watch: {
    autonomous () {
      this.sendDroneCommand({
        'autonomous': this.autonomous
      })
    },
    targetMode () {
      this.sendDroneCommand({
        'enroll_mode': !this.targetMode
      })
    },
    targetFace () {
      this.sendDroneCommand({
        'target_name': this.targetFace.split('.')[0]
      })
    },
  },
  created () {
    this.$http.get(this.BASE_URL + '/known_faces').then(response => {
      this.faces = response.body.filenames
    })
    setInterval(() => {
      this.$http.get(this.BASE_URL + '/known_faces').then(response => {
        this.faces = response.body.filenames
      })
    }, 5000)

    setInterval(() => {
      this.$http.get(this.BASE_URL + '/drone_status').then(response => {
        if (!this.connected) {
          this.$notify.success({
            title: 'Connection established',
            duration: 2000
          })
        }

        this.connected = true
        let droneStatus = response.body       
        this.batteryPercent = parseInt(droneStatus.battery)
        this.flying = droneStatus.flying
        this.speedForBack = droneStatus.for_back_velocity
        this.speedLeftRight = droneStatus.left_right_velocity
        this.speedUpDown = droneStatus.up_down_velocity
        this.speedYaw = droneStatus.yaw_velocity
      }, response => {
        if (this.connected) {
          this.$notify.error({
            title: 'Lost connection',
            message: 'No connection to drone',
            duration: 2000
          })
        }
        this.connected = false
      })
    }, 500)

    window.addEventListener('keydown', event => {
      let payload = {}
      if (!this.autonomous) {
        if (event.key === 'w') { // w
          payload['for_back_velocity'] = v_directional
          this.speedForBack = v_directional
        } else if (event.key ===  's') { // s
          payload['for_back_velocity'] = -v_directional
          this.speedForBack = -v_directional
        }
  
        if (event.key === 'd') { // d
          payload['left_right_velocity'] = v_directional
          this.speedLeftRight = v_directional
        } else if (event.key ===  'a') { // a
          payload['left_right_velocity'] = -v_directional
          this.speedLeftRight = -v_directional
        }
  
        if (event.key === 'q') { // q
          payload['yaw_velocity'] = -v_yaw_pitch
          this.speedYaw = -v_yaw_pitch
        } else if (event.key ===  'e') { // e
          payload['yaw_velocity'] = v_yaw_pitch
          this.speedYaw = v_yaw_pitch
        }
  
        if (event.key === 'r') { // r
          payload['up_down_velocity'] = v_directional
          this.speedUpDown = v_directional
        } else if (event.key ===  'f') { // f
          payload['up_down_velocity'] = -v_directional
          this.speedUpDown = -v_directional
        }

        this.sendDroneCommand(payload)
      }
    })

    window.addEventListener('keyup', event => {
      const payload = {
        'for_back_velocity': 0,
        'left_right_velocity': 0,
        'yaw_velocity': 0,
        'up_down_velocity': 0
      }

      if (!this.autonomous) this.sendDroneCommand(payload)
    })
  }
}
</script>

<style lang="scss">
@import "~element-ui/lib/theme-chalk/index.css";

body {
  font-family: "Helvetica Neue", Helvetica, Arial ,sans-serif;
}

#app {
  h2, h3, h4, h5, h6 {
    margin: 0;
  }

  .video-card {
    .el-card__body {
      padding: 0;

      .el-image {
        width: 100%;

        .no-image-slot {
          width: 100%;
          height: 720px;

          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;

          background-color: #DCDFE6;
          i {
            font-size: 2rem;
          }
        }
      }
    }
  }

  .controls-card {
    margin-left: 1rem;
    width: 100%;

    .category {
      margin-bottom: 1rem;

      h5 {
        margin-bottom: .5rem;
      }

      .spacer {
        height: 1rem;
      }
    }

    .speed-tag {
      min-width: 4rem;
      margin-right: .5rem;
    }
  }

  .friends-card {
    margin-left: 1rem;
    margin-top: 1rem;
    width: 100%;

    min-height: 400px;

    .friends-list {
      display: flex;
      flex-wrap: wrap;

      &__item {
        width: 75px;
        margin-top: .5rem;
        margin-right: .5rem;

        &.active {
          border: 3px solid red;
        }

        img {
          width: 75px;
          flex-grow: 0;
        }
      }
    }
  }
}
</style>
