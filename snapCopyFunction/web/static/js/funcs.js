
jQuery( document ).ready( function( $ ) {
  // $() will work as an alias for jQuery() inside of this function
  // [ your code goes here ]

$(function () {

  // load data initially for key 
  var url = window.location.pathname;
  var id = url.substring(url.lastIndexOf('/') + 1);
  var u = '/dev/db_get/' + id ;

  if (id !== null && id !== undefined) {

  //var QRCodeByteArrayAsBase64 = '{{qrcode}}' ;
  //var src_loc = "image/png;base64," + QRCodeByteArrayAsBase64;
  
  var QRCodeByteArrayAsBase64 = '{{qrcode}}' ;
  // set qr code image
  $('#qrcode').attr('src', `data:image/png;base64,${QRCodeByteArrayAsBase64}`);


  // set qr code image
  //$('#qrcode').attr('src', src_loc);

  $.get(u).done(
    function(data, status){
      console.log("Data: " + data + "\nStatus: " + status);
      var obj = JSON.parse(data);
      console.log(obj);
      var numberofRowsforItems = 0;
      for (var i = 0; i < obj.length; i++) {

        var r = '<tr><td data-type="email">'+obj[i][2]+'</td><td>'+obj[i][3]+'</td><td><button data-type="copy" class="text-copy">Copy</button></td></tr>'
        $('#myTable tr:last').after(r);

        document.querySelectorAll('button[data-type="copy"]')
        .forEach(function(button){
            button.addEventListener('click', function(){
            let email = this.parentNode.parentNode
              .querySelector('td[data-type="email"]')
              .innerText;
            
            let tmp = document.createElement('textarea');
                tmp.value = email;
                tmp.setAttribute('readonly', '');
                tmp.style.position = 'absolute';
                tmp.style.left = '-9999px';
                document.body.appendChild(tmp);
                tmp.select();
                //document.execCommand('copy');
                navigator.clipboard.writeText(email)
                document.body.removeChild(tmp);
                console.log(`${email} copied.`);
                $(".copied-toast").text("Copied!").show().fadeOut(1200);
          });
      });
      
      }
    })};
    
    $(".copied-toast").hide();
    $(".text-copy").click(function () {
      var copiedtext = $(this).closest("tr").find(".copy-me").text();
      if (navigator.clipboard) {
          navigator.clipboard.writeText(copiedtext)
              .then(() => {
                  $(".copied-toast").text("Copied!").show().fadeOut(1200);
              })
              .catch((error) => {
                  $(".copied-toast").text("Not copied!").show().fadeOut(1200);
              });
      } else {
          $(".copied-toast").text("Not copied!").show().fadeOut(1200);
      }

  });

   $('#submit_btn').click(function () {

    var textarea = document.getElementById('w3review');

    v = $.trim(textarea.value);

    var mykey = document.getElementById('mykey').value;

    var currentdate = new Date();
    var datetime = currentdate.getDate() + "/"
    + (currentdate.getMonth()+1)  + "/" 
    + currentdate.getFullYear() + " @ "  
    + currentdate.getHours() + ":"  
    + currentdate.getMinutes() + ":" 
    + currentdate.getSeconds();

    //var q = '<input class="form-control" type="text" value="'+ v +'" ></input>'

    //$("#grp").append(q);


    var r = '<tr><td class="copy-me" data-type="email">'+v+'</td><td>'+datetime+'</td><td><button data-type="copy"><div class="text-copy">Copy</div></button></td></tr>'

    console.log(r)

    $('#myTable tr:last').after(r);

    document.querySelectorAll('button[data-type="copy"]')
      .forEach(function(button){
          button.addEventListener('click', function(){
          let email = this.parentNode.parentNode
            .querySelector('td[data-type="email"]')
            .innerText;
          
          let tmp = document.createElement('textarea');
              tmp.value = email;
              tmp.setAttribute('readonly', '');
              tmp.style.position = 'absolute';
              tmp.style.left = '-9999px';
              document.body.appendChild(tmp);
              tmp.select();
              //document.execCommand('copy');
              navigator.clipboard.writeText(email)
              document.body.removeChild(tmp);
              console.log(`${email} copied.`);
              $(".copied-toast").text("Copied!").show().fadeOut(1200);
        });
    });



    $.post("/dev/db_add",
    {
      key: mykey,
      content: textarea.value
    },
    function(data, status){
      console.log("Data: " + data + "\nStatus: " + status);

    });

    textarea.value = "";

  });

  $('#chat_btn').click(function () {

    var textarea = document.getElementById('w3review');

    v = $.trim(textarea.value);

    var mykey = document.getElementById('mykey').value;

    var currentdate = new Date();
    var datetime = currentdate.getDate() + "/"
    + (currentdate.getMonth()+1)  + "/" 
    + currentdate.getFullYear() + " @ "  
    + currentdate.getHours() + ":"  
    + currentdate.getMinutes() + ":" 
    + currentdate.getSeconds();

    //var q = '<input class="form-control" type="text" value="'+ v +'" ></input>'

    //$("#grp").append(q);


    var r = '<tr><td class="copy-me" data-type="email">'+v+'</td><td>'+datetime+'</td><td><button data-type="copy"><div class="text-copy">Copy</div></button></td></tr>'

    console.log(r)

    $('#myTable tr:last').after(r);

    document.querySelectorAll('button[data-type="copy"]')
      .forEach(function(button){
          button.addEventListener('click', function(){
          let email = this.parentNode.parentNode
            .querySelector('td[data-type="email"]')
            .innerText;
          
          let tmp = document.createElement('textarea');
              tmp.value = email;
              tmp.setAttribute('readonly', '');
              tmp.style.position = 'absolute';
              tmp.style.left = '-9999px';
              document.body.appendChild(tmp);
              tmp.select();
              //document.execCommand('copy');
              navigator.clipboard.writeText(email)
              document.body.removeChild(tmp);
              console.log(`${email} copied.`);
              $(".copied-toast").text("Copied!").show().fadeOut(1200);
        });
    });


    $.post("/dev/chat",
    {
      key: mykey,
      content: textarea.value
    },
    function(data, status){
      console.log("Data: " + data + "\nStatus: " + status);

      var r = '<tr><td class="copy-me" data-type="email">'+data['response']+'</td><td>'+datetime+'</td><td><button data-type="copy"><div class="text-copy">Copy</div></button></td></tr>'

      console.log(r)

      $('#myTable tr:last').after(r);

    });

    textarea.value = "";

  });

  $('#gen_btn').click(function () {

    $.get("/dev/generate").done(

    function(data, status){
      //$('#mykey2').value = data;
      //$('#mykey').value = data;
      console.log("\nStatus: " + status);
      $("body").html(data);

      var mykey = document.getElementById('mykey').value;
      link = '/dev/pages/' + mykey
      window.location.href= link;

    });
  });

});

} );
