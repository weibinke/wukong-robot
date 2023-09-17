// const cubism2Model = "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/shizuku/shizuku.model.json";
// const cubism4Model = "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/haru/haru_greeter_t03.model3.json";
// const cubism4Model = "/live2d/packages/haru/haru_greeter_t03.model3.json";
// const cubism4Model = "/live2d/packages/haru_greeter_pro_jp/haru_greeter_t05.model3.json";
const cubism4Model = "/live2d/packages/live2d-widget-model-haru01/assets/haru01.model.json";

const live2d = PIXI.live2d;
let model = null;

(async function main() {
    const canvas = document.getElementById("canvas");
    const container = document.getElementById("live2d-container");
    console.log(canvas)
    const app = new PIXI.Application({
        view: canvas,
        autoStart: true,
        resizeTo: container,
        backgroundColor: 0x00999999
    });

    model = await live2d.Live2DModel.from(cubism4Model)
    // 将Live2D模型的引用存储在全局变量中
    window.live2dModel = model;

    app.stage.addChild(model);

    const scaleX = container.offsetWidth / model.internalModel.width;
    const scaleY = container.offsetHeight / model.internalModel.height
    console.log(scaleX)
    console.log(scaleY)

    // 铺满布局
    model.scale.set(Math.min(scaleX, scaleY));

    model.anchor.set(0.5); // 设置模型的锚点为中心点
    model.x = container.offsetWidth / 2;
    model.y = container.offsetHeight / 2;

    draggable(model);
    addFrame(model)
    addHitAreaFrames(model)


    model.on("hit", (hitAreas) => {
        console.log(hitAreas);
        if(hitAreas=="Body"){
            model.motion("tap_body");
            // model.expression("f01");
        }else if(hitAreas=="Head"){
            model.motion("tap_head");
            // model.expression("f01");
        }
    });
})();

// 设置模型参数值，兼容处理cubism2.0和4.0版本，参考：https://github.com/guansss/pixi-live2d-display/issues/15
function setParameterValueById_Mouth(mode, value){
    if(typeof model.internalModel.coreModel.setParameterValueById === "function"){
        //cubism 4.0
        model.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", value); 
    }else if (typeof model.internalModel.coreModel.setParamFloat === "function"){
        //cubism 2.0
        model.internalModel.coreModel.setParamFloat("PARAM_MOUTH_OPEN_Y", value);
    }
}

// 通过控制嘴巴打开来模拟说话
// 设置嘴型。注意要Live2D模型得是3版本以上才可以，不然会报错找不找不到这个方法setParameterValueById
// model.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', 1);
let startTime;
function talking_with_MouthOpen() {
    // 每100毫秒随机改变嘴巴的开合程度
    startTime = Date.now();
    const talkInterval = setInterval(() => {
        console.log("talking_with_MouthOpen:" + isTalking);
        if (isTalking) {
            const time = Date.now() - startTime;
            const mouthOpenY = (Math.sin(time / 200) + 1) / 2;  // 生成一个周期性变化的数，/200 ，这个数越小，动作越快
            // const mouthOpenY = Math.random();  // 生成一个0到1之间的随机数
            console.log(mouthOpenY);
            setParameterValueById_Mouth(model,mouthOpenY);
        } else {
            // 停止改变嘴巴的开合程度
            clearInterval(talkInterval);
            // 将嘴巴的开合程度设置为0（闭合）
            setParameterValueById_Mouth(model,0)
        }

    }, 100);
}

// 通过循环motion的动作来模拟说话
function talk_with_motion() {
    model.motion("talk");
    model.internalModel.motionManager.on('motionStart', (group, index, audio) => {
        console.log("motionStart group=" + group);
    });
    model.internalModel.motionManager.on('motionFinish', () => {
        console.log("motionFinish");
        if (isTalking) {
            setTimeout(() => {
                model.motion("talk");
            }, 0);
        }
    });
}

let isTalking = false;
export function startTalking() {
    const model = window.live2dModel;
    if (model && !isTalking) {
        isTalking = true;
        // talk_with_motion();
        talking_with_MouthOpen();
        // Check the talking status after a certain delay
        setTimeout(checkTalkingStatus, 1000); // Adjust the delay as needed
    }
}

function stopTalking() {
    console.log("stopTalking")
    isTalking = false;
}

function checkTalkingStatus() {
    const model = window.live2dModel;
    if (model && isTalking) {

        $.ajax({
            url: '/talk_status',
            type: "GET",
            data: $.param({ 'validate': getCookie('validation') }),
            success: function (res) {
                var data = JSON.parse(res);
                const isTalkingStatus = data.isTalking; // Assuming the API response contains a boolean property 'isTalking'
                console.log("checkTalkingStatus result:" + isTalking);
                if (isTalkingStatus == "True") {
                    // The model is still talking, continue playing the talking motion
                    setTimeout(checkTalkingStatus, 1000); // Recursively call the function to check the status again after a delay
                } else {
                    // The model has stopped talking, restart the animation
                    stopTalking();
                }
            },
            error: function () {
                toastr.error('服务器异常', '获取播放状态失败');
                stopTalking();
            }
        });
    }
}

function draggable(model) {
    model.buttonMode = true;
    model.on("pointerdown", (e) => {
        model.dragging = true;
        model._pointerX = e.data.global.x - model.x;
        model._pointerY = e.data.global.y - model.y;
    });
    model.on("pointermove", (e) => {
        if (model.dragging) {
            model.position.x = e.data.global.x - model._pointerX;
            model.position.y = e.data.global.y - model._pointerY;
        }
    });
    model.on("pointerupoutside", () => (model.dragging = false));
    model.on("pointerup", () => (model.dragging = false));
}

function addFrame(model) {
    const foreground = PIXI.Sprite.from(PIXI.Texture.WHITE);
    foreground.width = model.internalModel.width;
    foreground.height = model.internalModel.height;
    foreground.alpha = 0.2;

    model.addChild(foreground);

    checkbox("Model Frames", (checked) => (foreground.visible = checked));
}

function addHitAreaFrames(model) {
    const hitAreaFrames = new live2d.HitAreaFrames();

    model.addChild(hitAreaFrames);

    checkbox("Hit Area Frames", (checked) => (hitAreaFrames.visible = checked));
}

function checkbox(name, onChange) {
    const id = name.replace(/\W/g, "").toLowerCase();

    let checkbox = document.getElementById(id);

    if (!checkbox) {
        const p = document.createElement("p");
        p.innerHTML = `<input type="checkbox" id="${id}"> <label for="${id}">${name}</label>`;

        document.getElementById("frame_control").appendChild(p);
        checkbox = p.firstChild;
    }

    checkbox.addEventListener("change", () => {
        onChange(checkbox.checked);
    });

    onChange(checkbox.checked);

}
