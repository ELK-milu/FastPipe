# FastPipe 🚀

一个高度自定义化的可并发的流式响应的PipeLine服务框架。可用于AI服务间的交互。

------

## 特性

- 内外输出逻辑分离——数据在modules内的传输逻辑是分离的，你可以让Module将处理好的数据一边用json包装成响应格式让服务端返回流式响应；一边将未包装的数据传递给下一个功能模块。就不需要在客户端将不同API返回的请求拆包再封装传递
- 异步并发——框架代码全部用异步完成，支持快速并发处理。用httpx实现连接池管理。
- 模块化设计——模块是独立的，你可以在启动pipeline服务时将module进行组合，实现各种工作流的逻辑，只需要保证模块连接时的输出类型和输出类型匹配即可。由于不同模块是高度解耦的，只负责单一服务。所以你可以在任何地方调用这些模块。
- 高自由度——你可以使用预设的Module，也可以自己编写Module，只需要为模块通过继承并实现抽象方法和重写函数实现自定义，这完全取决于你的需要。

内置了一些基本服务，如sqlalchemy，httpx，rabbitmq


--------

## 快速开始

通过`pip install requirements.txt`安装依赖

在pipeline目录下输入下列命令启动服务

```bash
python main.py
```

启动项的配置和两个文件相关，一个是`setting/__init__.py`，有关dataset，rabbitmq，redis等微服务，以及启动服务的host和port等一些服务启动项的配置存放在里面。

另一个是`Configs/Config.yaml`，有关模块启动项的配置存放在里面，用于配置发送请求的ip，key之类的全局信息

除了这些全局选项之外，你还可以在`services/`里面找到一些其他的模块服务配置文件`Config.yaml`。这些配置文件可以自由定义，并由模块内部单独读取后解析为字典。用于模块内一些逻辑的开发和使用


你可以通过在`main.py`代码中添加或删除模块来选择pipeline启用的服务：
```python
pipeline = PipeLine.create_pipeline(
    Dify_LLM_Module,
    GPTSoVit_TTS_Module
)
```

服务启动时会根据你当前使用的Pipeline进行连接可行性验证，只需要保证模型需要的输入类型和输出类型相符即可：

```bash
✅ Pipeline验证通过
当前Pipeline: Ollama_LLM_Module -> GPTSoVit_TTS_Module
类型详情:
Ollama_LLM_Module (输入: <class 'str'>, 输出: <class 'str'>)
GPTSoVit_TTS_Module (输入: <class 'str'>, 输出: <class 'bytes'>)
```

在自定义模块的时候，需要继承基类`BaseModule`，路径位于`modules/__init__.py`,并实现其中的抽象方法

`main_loop`是模块执行的主逻辑，模块在main_loop中可以处理数据并分别丢给pipeline和下一个module的信息，可以通过`PutToPipe`封装为pipeline解析用的数据类`AsyncQueueMessage`放入pipeline。
通过封装为`ModuleMessage`数据类丢入`nextModel.ModuleEntry`作为下一个模块的输入。

服务端的post请求所需的基础参数如下：
```bash
class PipeLineRequest(RequestModel):
    model_config = ConfigDict(extra='allow')
    # Required fields
    user: str
    Input: str
    text:str
    Entry: int

    conversation_id: str = ""
    message_id: str = ""
```

`streamly`代表了是否是流式请求(服务端目前返回的始终是流式的)。

`user`是用户标识，通过user名这一字符串来管理用户线程和请求

`Input`是任意类型输入，可以是一些文件，目前暂未使用

`text` 是用户输入的文本内容

`Entry`是服务入口，以0为起点。通过这个标识来告知服务器你的请求是从哪个模块进入的

`conversation_id` 是当前会话id，可为空
`message_id` 是上一条消息id，可为空

------------

## 项目结构：

1. Configs 这里存放了各个功能模块的启动的配置yaml文件，由`settings/__init__.py`读取到CONFIG中，可以通过修改CONFIG_NAME来切换读取的CONFIG文件。
2. hooks 这里存放了fastapi的生命周期管理`lifespan.py`，以及一些其他的钩子函数，例如请求时调用的中间件`middlewares.py`，用于注入依赖的`dependencies.py`等
3. logs 这里存放了loguru产生的日志文件
4. models 这里存放数据模型类，用于orm解析，属于mvc中的model部分
5. modules 这里存放了各个功能模块的代码，包括`BaseModule`和`pipeline`。通过继承`BaseModule`来实现自定义模块。可理解为mvc中的model部分
6. services 这里存放了功能模块的服务代码和数据处理代码，属于mvc中的controller部分。
7. routers 这里存放了fastapi的路由代码，负责处理请求和响应。属于mvc中的view部分。
在定义一个模块时，通常是先定义一个modules中的模块类，实现一些抽象方法。将大部分的数据处理和创建session的逻辑放在services中。将一些其他的restful api定义相关和接口实现放在routers中。这样可以将模块的逻辑和路由的逻辑分离，便于维护和扩展。
8. resource 存放了服务端的静态资源
9. settings 存放了服务端启动的配置文件
10. utils 这里存放了一些工具库和类，例如rabbitmq，snowflake等


## 贡献者

欢迎来为这个项目作出贡献，杰出的贡献者将会被口头表扬

<table>
    <tr>
        <td align="center">
            <a href="https://github.com/ELK-milu">
                <img src="https://avatars.githubusercontent.com/u/56761558?v=4" width="100px;" alt="" style="max-width: 100%;">
                <br>
                <sub>
                    <b>ELK-milu</b>
                </sub>
            </a>
        </td>
    </tr>
</table>

